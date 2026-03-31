#!/usr/bin/env python3
"""
apply_c1_patch.py  —  Sprint C1 patch for main.py
Run from your repo root:  python apply_c1_patch.py
"""

import re
import sys
import shutil
from pathlib import Path

MAIN = Path("main.py")

if not MAIN.exists():
    print("❌  main.py not found — run this from your repo root")
    sys.exit(1)

# Backup
shutil.copy(MAIN, "main.py.bak")
print("✅  Backed up to main.py.bak")

src = MAIN.read_text()
original = src  # keep for diff check

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — import
# ─────────────────────────────────────────────────────────────────────────────

IMPORT_ANCHOR = "from antar_engine.predictions import ("
IMPORT_NEW    = "from plain_english import generate_plain_english\n\n"

if "from plain_english import generate_plain_english" in src:
    print("⚠️   Change 1 already applied — skipping import")
elif IMPORT_ANCHOR not in src:
    print("❌  Change 1 FAILED — could not find anchor:\n   ", IMPORT_ANCHOR)
    sys.exit(1)
else:
    src = src.replace(IMPORT_ANCHOR, IMPORT_NEW + IMPORT_ANCHOR, 1)
    print("✅  Change 1 applied — import added")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 — call plain_english after LLM response
# ─────────────────────────────────────────────────────────────────────────────

LLM_PRINT = (
    '    print(f"[predict] LLM response len='
    '{len(prediction_text) if prediction_text else 0} concern={concern}")'
)

PE_BLOCK = '''
    # ── C1: Plain English post-processing ────────────────────────
    _pe = None
    try:
        _pe = await generate_plain_english(
            raw_prediction=prediction_text or "",
            chart_context={
                "lagna":   chart_record.get("lagna_sign"),
                "dasha":   chart_record.get("current_dasha"),
                "age":     getattr(patra, "age", None),
                "country": chart_record.get("birth_country"),
                "concern": concern,
            },
        )
        print(f"[predict] plain_english ok — signal=\'{(_pe or {}).get('signal_line','')[:60]}\'")
    except Exception as _pe_err:
        print(f"[predict] plain_english failed (non-fatal): {_pe_err}")
        _pe = None
    # ── end C1 ───────────────────────────────────────────────────
'''

if "_pe = await generate_plain_english" in src:
    print("⚠️   Change 2 already applied — skipping plain_english call")
elif LLM_PRINT not in src:
    print("❌  Change 2 FAILED — could not find anchor:\n   ", LLM_PRINT)
    sys.exit(1)
else:
    src = src.replace(LLM_PRINT, LLM_PRINT + PE_BLOCK, 1)
    print("✅  Change 2 applied — plain_english wired into /predict")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3 — add new fields to the existing DB insert
# ─────────────────────────────────────────────────────────────────────────────

DB_ANCHOR = '            "chart_id":    chart_id,\n            "concern":     concern,\n        }).execute()'
DB_NEW    = (
    '            "chart_id":          chart_id,\n'
    '            "concern":           concern,\n'
    '            "plain_summary":     _pe.get("plain_summary")   if _pe else None,\n'
    '            "action_item":       _pe.get("action_item")     if _pe else None,\n'
    '            "signal_line":       _pe.get("signal_line")     if _pe else None,\n'
    '            "timing_window":     _pe.get("timing_window")   if _pe else None,\n'
    '            "signal_confidence": _pe.get("confidence")      if _pe else None,\n'
    '            "all_domains":       _pe.get("all_domains")     if _pe else [],\n'
    '        }).execute()'
)

if '"plain_summary":' in src:
    print("⚠️   Change 3 already applied — skipping DB insert update")
elif DB_ANCHOR not in src:
    # Try alternate spacing
    DB_ANCHOR2 = '            "chart_id":   chart_id,\n            "concern":    concern,\n        }).execute()'
    if DB_ANCHOR2 in src:
        src = src.replace(DB_ANCHOR2, DB_NEW, 1)
        print("✅  Change 3 applied (alt spacing) — DB insert updated")
    else:
        print("❌  Change 3 FAILED — could not find DB insert anchor.")
        print("    Look for the supabase predictions insert and manually add:")
        print('            "plain_summary":     _pe.get("plain_summary")   if _pe else None,')
        print('            "action_item":       _pe.get("action_item")     if _pe else None,')
        print('            "signal_line":       _pe.get("signal_line")     if _pe else None,')
        print('            "timing_window":     _pe.get("timing_window")   if _pe else None,')
        print('            "signal_confidence": _pe.get("confidence")      if _pe else None,')
        print('            "all_domains":       _pe.get("all_domains")     if _pe else [],')
else:
    src = src.replace(DB_ANCHOR, DB_NEW, 1)
    print("✅  Change 3 applied — 6 new fields added to DB insert")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 4 — add two new endpoints at end of file
# ─────────────────────────────────────────────────────────────────────────────

NEW_ENDPOINTS = '''

# ── C1: Prediction history endpoint ──────────────────────────────────────────
@app.get("/api/v1/predictions/{chart_id}")
async def get_prediction_history(chart_id: str, limit: int = 20):
    """Last N predictions for a chart with plain English output. Sprint C1-03."""
    try:
        result = supabase.table("predictions") \\
            .select(
                "id, created_at, query, concern, "
                "plain_summary, action_item, signal_line, "
                "timing_window, signal_confidence, all_domains"
            ) \\
            .eq("chart_id", chart_id) \\
            .order("created_at", desc=True) \\
            .limit(min(limit, 50)) \\
            .execute()
        predictions = result.data or []
        return {"predictions": predictions, "total": len(predictions)}
    except Exception as e:
        print(f"[predictions] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch prediction history")


# ── C1: Domain signals endpoint ───────────────────────────────────────────────
@app.get("/api/v1/domain-signals/{chart_id}")
async def get_domain_signals(chart_id: str):
    """One signal_line per life domain from most recent prediction. Sprint C1-04."""
    domains = [
        "career", "wealth", "love", "children", "health", "foreign",
        "legal", "business", "loans", "property", "education", "luck",
        "travel", "spirituality", "father", "mother", "siblings",
        "enemies", "general"
    ]
    try:
        result = supabase.table("predictions") \\
            .select("id, concern, signal_line, signal_confidence, timing_window, all_domains, created_at") \\
            .eq("chart_id", chart_id) \\
            .not_.is_("signal_line", "null") \\
            .order("created_at", desc=True) \\
            .limit(100) \\
            .execute()
        predictions = result.data or []
        signals = {}
        for domain in domains:
            for pred in predictions:
                pred_domains = pred.get("all_domains") or []
                if domain in pred_domains or domain == pred.get("concern"):
                    signals[domain] = {
                        "signal_line":   pred.get("signal_line"),
                        "confidence":    pred.get("signal_confidence"),
                        "timing_window": pred.get("timing_window"),
                        "prediction_id": pred.get("id"),
                        "created_at":    pred.get("created_at"),
                    }
                    break
        return {
            "signals":      signals,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[domain-signals] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch domain signals")
'''

if '"/api/v1/predictions/{chart_id}"' in src:
    print("⚠️   Change 4 already applied — skipping new endpoints")
else:
    src = src.rstrip() + "\n" + NEW_ENDPOINTS + "\n"
    print("✅  Change 4 applied — /predictions and /domain-signals endpoints added")

# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

if src == original:
    print("\n⚠️   No changes were written — all steps were already applied or failed.")
else:
    MAIN.write_text(src)
    print(f"\n✅  main.py updated. Backup at main.py.bak")
    print("    Next: git add plain_english.py main.py && git commit -m 'feat(C1): plain english engine' && git push")
