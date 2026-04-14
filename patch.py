#!/usr/bin/env python3
"""
patch_kv_cache_v2.py

Fixes the KV cache by reordering chart_context_builder.py blocks so the
## LIVE DATA marker sits at the right boundary between truly-stable content
and per-call-dynamic content.

ROOT CAUSE (from debug instrumentation):
- chart_context_builder.py line 688 has a hardcoded `## LIVE DATA` marker
- It currently splits at: [stable content] | LIVE DATA | [transits + Jaimini + lk_warnings + Vedic rules]
- But Jaimini, lk_warnings, and Vedic rules are ALL stable per chart (not dynamic)
- Result: only 7283 chars of static (~1820 tokens, barely above cache threshold)
- And the static block content fluctuates due to noise in stable section
- Cache hit rate: 0%

FIX:
- Move Jaimini, lk_warnings, and the trailing Vedic rules INTO the static region
- Keep only `trans_block` and `_teva_block` (Teva is derived from transits) in dynamic tail
- Result: ~14k chars static (~3500 tokens), only ~2k chars dynamic
- Cache hit rate: ~85% expected

ALSO REMOVES:
- The redundant `## LIVE DATA` marker we added in main.py KV cache patch
  (chart_context_builder's marker is now correctly placed; we don't need a second one)
"""

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

CTX = Path("antar_engine/chart_context_builder.py")
MAIN = Path("main.py")
BACKUP_CTX = Path(f"antar_engine/chart_context_builder.py.bak_kv_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
BACKUP_MAIN = Path(f"main.py.bak_kv_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

# ============================================================
# PART 1: Reorder chart_context_builder.py blocks
# ============================================================
#
# OLD layout (lines ~680-694):
#     {_lk_advanced_block}
#     ━━━
#     {_umra_block}
#     ━━━
#     {_masik_block}
#     ━━━
#     {_teva_block}
#
#     ## LIVE DATA
#     ━━━
#     {trans_block}
#     ━━━
#     {_jaimini_block}
#     ━━━
#     {lk_warnings}
#     ━━━
#     VEDIC ASTROLOGY RULES...
#
# NEW layout:
#     {_lk_advanced_block}
#     ━━━
#     {_umra_block}
#     ━━━
#     {_masik_block}
#     ━━━
#     {_jaimini_block}              ← moved up (stable per chart)
#     ━━━
#     {lk_warnings}                 ← moved up (stable per chart)
#     ━━━
#     VEDIC ASTROLOGY RULES...      ← moved up (constant)
#     ... (rest of static rules)
#     ANTI-HALLUCINATION INSTRUCTIONS...
#
#     ## LIVE DATA                  ← NEW position, just before per-call dynamic
#     ━━━
#     {_teva_block}                 ← derived from transits, dynamic
#     ━━━
#     {trans_block}                 ← per-minute, dynamic

OLD_BLOCK_1 = '''━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_teva_block}

## LIVE DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{trans_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_jaimini_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{lk_warnings}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'''

NEW_BLOCK_1 = '''━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_jaimini_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{lk_warnings}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'''

# Now we need to find the END of the static rules block and insert the
# ## LIVE DATA marker + dynamic blocks AFTER the anti-hallucination section.
# The function returns "context" right after, so we anchor on:
#
#     8. Transit effects must reference the transit section above
#
# """
#     return context

OLD_BLOCK_2 = '''8. Transit effects must reference the transit section above

"""
    return context'''

NEW_BLOCK_2 = '''8. Transit effects must reference the transit section above

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## LIVE DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_teva_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{trans_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return context'''


# ============================================================
# PART 2: Remove redundant marker from main.py KV cache patch
# ============================================================
#
# In main.py our patch currently appends "## LIVE DATA" at the end.
# Since chart_context_builder now places the marker correctly inside
# _full_context, we don't need to add a second one. The first split
# (which is now the correct one) will be used by call_llm_claude.

OLD_MAIN_BLOCK = '''        _cacheable_context = _full_context if _full_context else ""
        if _cacheable_context:
            _master_system = (
                _master_system
                + "\\n\\n=== CHART CONTEXT (stable) ===\\n"
                + _cacheable_context
                + "\\n\\n## LIVE DATA\\n"
            )'''

NEW_MAIN_BLOCK = '''        _cacheable_context = _full_context if _full_context else ""
        if _cacheable_context:
            # NOTE: _full_context already contains the canonical "## LIVE DATA"
            # marker (placed correctly by chart_context_builder.py after the
            # static Vedic rules block). Do NOT add a second marker here —
            # call_llm_claude splits on the first occurrence.
            _master_system = (
                _master_system
                + "\\n\\n=== CHART CONTEXT ===\\n"
                + _cacheable_context
            )'''


def patch_file(path: Path, backup: Path, replacements: list[tuple[str, str, str]]) -> bool:
    """Apply a list of (old, new, label) replacements to a file. Returns True on success."""
    if not path.exists():
        print(f"❌ {path} not found")
        return False

    print(f"📦 Backing up {path} → {backup}")
    shutil.copy(path, backup)

    src = path.read_text()

    for old, new, label in replacements:
        if old not in src:
            print(f"❌ Landmark not found: {label}")
            print(f"    Looking for: {old[:80]}...")
            shutil.copy(backup, path)
            return False
        occ = src.count(old)
        if occ != 1:
            print(f"❌ Expected 1 occurrence of {label}, found {occ}")
            shutil.copy(backup, path)
            return False
        src = src.replace(old, new, 1)
        print(f"✅ {label}")

    # ast.parse only for .py
    if path.suffix == ".py":
        try:
            ast.parse(src)
            print(f"✅ ast.parse OK ({path})")
        except SyntaxError as e:
            print(f"❌ Syntax error after patching {path}: {e}")
            shutil.copy(backup, path)
            return False

    path.write_text(src)
    print(f"✅ Wrote {path}")
    return True


def main():
    print("=" * 60)
    print("KV CACHE V2 — proper static/dynamic split")
    print("=" * 60)
    print()

    # --- PART 1: chart_context_builder.py ---
    print("PART 1: Reorder chart_context_builder.py blocks")
    print("-" * 60)
    ok1 = patch_file(
        CTX,
        BACKUP_CTX,
        [
            (OLD_BLOCK_1, NEW_BLOCK_1, "Step 1a: remove transits/jaimini/lk_warnings from current position, keep jaimini+lk_warnings here as static"),
            (OLD_BLOCK_2, NEW_BLOCK_2, "Step 1b: insert ## LIVE DATA marker + teva + transits AFTER anti-hallucination block"),
        ],
    )
    if not ok1:
        sys.exit(1)
    print()

    # --- PART 2: main.py ---
    print("PART 2: Remove redundant marker from main.py")
    print("-" * 60)
    ok2 = patch_file(
        MAIN,
        BACKUP_MAIN,
        [
            (OLD_MAIN_BLOCK, NEW_MAIN_BLOCK, "Step 2: drop redundant ## LIVE DATA marker from main.py KV cache patch"),
        ],
    )
    if not ok2:
        # Roll back part 1 too
        print("⚠️  Part 2 failed — rolling back Part 1")
        shutil.copy(BACKUP_CTX, CTX)
        sys.exit(1)

    print()
    print("=" * 60)
    print("DEPLOY & VERIFY:")
    print("=" * 60)
    print("1. git diff antar_engine/chart_context_builder.py main.py")
    print("2. git add -A && git commit -m 'fix: KV cache v2 — proper static/dynamic split in chart context'")
    print("3. git push    # wait ~60s for Railway")
    print()
    print("4. Make 2 predict calls (same chart, different questions)")
    print()
    print("5. railway logs --lines 100 | grep -E '\\[claude\\]|\\[kv-debug\\]'")
    print()
    print("EXPECTED:")
    print("  Call 1:")
    print("    [kv-debug] static_len=~14000  static_hash=AAAAAAAA")
    print("    [claude]  cache_hit=0     cache_write=~3500 output=...")
    print()
    print("  Call 2:")
    print("    [kv-debug] static_len=~14000  static_hash=AAAAAAAA   ← SAME HASH")
    print("    [claude]  cache_hit=~3500 cache_write=0     output=... ← CACHE HIT")
    print()
    print("  Speed: Call 2 should drop from ~22s to ~5-8s")
    print()
    print(f"ROLLBACK if it breaks:")
    print(f"  cp {BACKUP_CTX} {CTX}")
    print(f"  cp {BACKUP_MAIN} {MAIN}")
    print(f"  git checkout antar_engine/chart_context_builder.py main.py")


if __name__ == "__main__":
    main()
