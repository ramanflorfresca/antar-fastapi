#!/usr/bin/env python3
"""
apply_c4_patch.py — Sprint C4 patch for main.py
Run from repo root: python apply_c4_patch.py

Changes:
  1. Add common_sense import
  2. Wire C4 block into /predict after C3 memory block
  3. Inject C4 block into the prompt
"""

import shutil
import sys
from pathlib import Path

MAIN = Path("main.py")
if not MAIN.exists():
    print("❌  main.py not found — run from repo root")
    sys.exit(1)

shutil.copy(MAIN, "main.py.bak_c4")
print("✅  Backed up to main.py.bak_c4")

src = MAIN.read_text()

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — import
# ─────────────────────────────────────────────────────────────────────────────

IMPORT_ANCHOR = "from antar_engine.pattern_memory import build_pattern_memory"
IMPORT_NEW = (
    "from antar_engine.pattern_memory import build_pattern_memory\n"
    "from antar_engine.common_sense import build_common_sense_block"
)

if "from antar_engine.common_sense import build_common_sense_block" in src:
    print("⚠️   Change 1 already applied — skipping import")
elif IMPORT_ANCHOR not in src:
    print("❌  Change 1 FAILED — pattern_memory import not found")
    sys.exit(1)
else:
    src = src.replace(IMPORT_ANCHOR, IMPORT_NEW, 1)
    print("✅  Change 1 applied — common_sense import added")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 — wire C4 after C3 memory block
# ─────────────────────────────────────────────────────────────────────────────

ANCHOR_C3_END = "    # ── end C3 ───────────────────────────────────────────────────"

C4_BLOCK = """    # ── end C3 ───────────────────────────────────────────────────

    # ── C4: Common Sense Layer ───────────────────────────────────
    _cs_block = ""
    try:
        _cs_block = build_common_sense_block(
            age=getattr(patra, "age", None),
            life_stage=getattr(patra, "life_stage_name", None),
            concern=concern,
            country_code=country_code,
            marital_status=user_profile.get("marital_status"),
            children_status=user_profile.get("children_status"),
            dkp_context=dkp_context,
            memory_result=_memory,
        )
        if _cs_block:
            print(f"[predict] C4 common sense — {len(_cs_block)} chars")
    except Exception as _cs_err:
        print(f"[predict] C4 common sense failed (non-fatal): {_cs_err}")
        _cs_block = ""
    # ── end C4 ───────────────────────────────────────────────────"""

if "C4: Common Sense Layer" in src:
    print("⚠️   Change 2 already applied — skipping C4 block")
elif ANCHOR_C3_END not in src:
    print("❌  Change 2 FAILED — C3 end anchor not found")
    sys.exit(1)
else:
    src = src.replace(ANCHOR_C3_END, C4_BLOCK, 1)
    print("✅  Change 2 applied — C4 block wired into /predict")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3 — inject C4 block into the prompt (alongside C3)
# ─────────────────────────────────────────────────────────────────────────────

INJECT_ANCHOR = "    # ── C3: Append memory + diagnostic blocks to prompt ─────────"

INJECT_NEW = """    # ── C3 + C4: Append memory, diagnostic, and common sense to prompt ──
    _memory_block     = (_memory or {}).get("memory_block", "")
    _diagnostic_block = (_memory or {}).get("diagnostic_block", "")

    for _block in [_memory_block, _diagnostic_block, _cs_block]:
        if not _block:
            continue
        if _full_context:
            _full_context += f"\\n\\n{_block}"
        else:
            prompt += f"\\n\\n{_block}"
    # ── end C3+C4 injection ───────────────────────────────────────"""

# Remove old C3 injection block and replace with combined one
OLD_INJECT = """    # ── C3: Append memory + diagnostic blocks to prompt ─────────
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
    # ── end C3 memory injection ───────────────────────────────────"""

if "C3 + C4: Append memory" in src:
    print("⚠️   Change 3 already applied — skipping prompt injection")
elif OLD_INJECT in src:
    src = src.replace(OLD_INJECT, INJECT_NEW, 1)
    print("✅  Change 3 applied — C3+C4 blocks injected into prompt")
elif INJECT_ANCHOR in src:
    # Fallback — just replace the header line
    src = src.replace(INJECT_ANCHOR, INJECT_NEW, 1)
    print("✅  Change 3 applied (fallback) — C4 added to prompt injection")
else:
    print("⚠️   Change 3 — injection anchor not found")
    print("     Manually add _cs_block to the prompt injection section")

# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

MAIN.write_text(src)
print(f"\n✅  main.py updated. Backup at main.py.bak_c4")
print("    Next:")
print("    1. cp common_sense.py antar_engine/common_sense.py")
print("    2. git add antar_engine/common_sense.py main.py")
print("    3. git commit -m 'feat(C4): common sense layer'")
print("    4. git push")
print("    5. python test_c3_c4.py")
