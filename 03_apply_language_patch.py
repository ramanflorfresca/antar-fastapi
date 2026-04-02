#!/usr/bin/env python3
"""
Antar Language Patch v2 — Auto-Discovery
=========================================
Finds main.py and prashna_engine.py automatically.
Run from your project root (antarai/).

Usage:
  python 03_apply_language_patch_v2.py

What it does:
  1. Finds main.py and antar_engine/prashna_engine.py
  2. Copies language_utils.py into place (if 02_language_utils.py exists)
  3. Patches main.py: adds import + update-preferences endpoint
  4. Patches prashna_engine.py: adds language param to signatures + prompt injection
  5. Prints manual wiring instructions for /predict, /prashna, /daily-signal
"""

import os
import sys
import re
import shutil
import glob
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════
# AUTO-DISCOVERY
# ═══════════════════════════════════════════════════════════════════

def find_file(name, search_dirs=None):
    """Find a file by name in common locations."""
    if search_dirs is None:
        search_dirs = [
            ".",
            "antar_engine",
            "app",
            "src",
            "api",
            "backend",
        ]

    for d in search_dirs:
        path = os.path.join(d, name)
        if os.path.exists(path):
            return path

    # Try glob as fallback
    results = glob.glob(f"**/{name}", recursive=True)
    if results:
        return results[0]

    return None


def backup(filepath):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bp = f"{filepath}.backup_{ts}"
    shutil.copy2(filepath, bp)
    print(f"  ✓ Backup: {bp}")
    return bp


def read_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath, content):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


# ═══════════════════════════════════════════════════════════════════
# STEP 0: Copy language_utils.py into place
# ═══════════════════════════════════════════════════════════════════

def setup_language_utils(main_py_dir):
    """Copy 02_language_utils.py as language_utils.py next to main.py."""
    target = os.path.join(main_py_dir, "language_utils.py")

    if os.path.exists(target):
        print(f"  · language_utils.py already exists at {target}")
        return True

    # Look for the source file
    sources = [
        "02_language_utils.py",
        os.path.join(main_py_dir, "02_language_utils.py"),
    ]
    for src in sources:
        if os.path.exists(src):
            shutil.copy2(src, target)
            print(f"  ✓ Copied {src} → {target}")
            return True

    # Not found — create it inline
    print(f"  ⚠ 02_language_utils.py not found — creating language_utils.py directly")
    write_file(target, LANGUAGE_UTILS_CONTENT)
    print(f"  ✓ Created {target}")
    return True


# ═══════════════════════════════════════════════════════════════════
# INLINE language_utils.py content (fallback if file not found)
# ═══════════════════════════════════════════════════════════════════

LANGUAGE_UTILS_CONTENT = '''"""
Antar Language Utilities
"""

VALID_LANGUAGES = {"en", "hi", "hinglish", "es", "pt"}
VALID_REMEDY_STYLES = {"traditional", "secular"}

_LANGUAGE_BLOCKS = {
    "hi": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Hindi using Devanagari script.\\n"
        "Use formal, respectful Hindi. Do not mix in English words.\\n"
        "All numbers, dates, percentages in standard numerals (87%, April 15).\\n"
        "Never translate: Antar, Seeker, Navigator.\\n"
        "No Sanskrit astrological terms — use plain Hindi.\\n\\n"
    ),
    "hinglish": (
        "LANGUAGE INSTRUCTION: Respond in Hinglish — casual Hindi-English mix in Roman script.\\n"
        "Example: 'Aapka career energy abhi peak pe hai. Next 3 weeks mein bold move karo.'\\n"
        "Mix naturally. Numbers/dates in standard format.\\n"
        "Never translate: Antar, Seeker, Navigator.\\n\\n"
    ),
    "es": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Latin American Spanish.\\n"
        "Professional, clear. No European Spanish (no vosotros).\\n"
        "Never revert to English mid-sentence.\\n"
        "Numbers/dates in standard format. Never translate: Antar, Seeker, Navigator.\\n\\n"
    ),
    "pt": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Brazilian Portuguese.\\n"
        "Professional, clear. Not European Portuguese.\\n"
        "Never revert to English mid-sentence.\\n"
        "Numbers/dates in standard format. Never translate: Antar, Seeker, Navigator.\\n\\n"
    ),
}

def build_language_instruction(language="en"):
    if not language or language == "en":
        return ""
    return _LANGUAGE_BLOCKS.get(language, "")

def resolve_language(request_body=None, chart_data=None):
    if request_body:
        lang = request_body.get("language")
        if lang and lang in VALID_LANGUAGES:
            return lang
    if chart_data:
        stored = chart_data.get("language")
        if stored and stored in VALID_LANGUAGES:
            return stored
    return "en"

def resolve_language_from_query(query_params, chart_data=None):
    lang = None
    if query_params:
        lang = query_params.get("language") if hasattr(query_params, 'get') else None
    if lang and lang in VALID_LANGUAGES:
        return lang
    if chart_data:
        stored = chart_data.get("language")
        if stored and stored in VALID_LANGUAGES:
            return stored
    return "en"
'''


# ═══════════════════════════════════════════════════════════════════
# PATCH main.py
# ═══════════════════════════════════════════════════════════════════

UPDATE_PREFS_ENDPOINT = '''

# ═══════════════════════════════════════════════════════════════════
# USER PREFERENCES — Language + Remedy Style (Sprint L)
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/v1/chart/update-preferences")
async def update_preferences(request: Request):
    """Update user language and remedy_style preferences."""
    try:
        body = await request.json()
        chart_id = body.get("chart_id")

        if not chart_id:
            return JSONResponse(status_code=400, content={"error": "chart_id is required"})

        valid_languages = {"en", "hi", "hinglish", "es", "pt"}
        language = body.get("language")
        if language and language not in valid_languages:
            return JSONResponse(status_code=400,
                content={"error": f"Invalid language. Must be one of: {', '.join(sorted(valid_languages))}"})

        remedy_style = body.get("remedy_style")
        if remedy_style is not None and remedy_style not in {"traditional", "secular"}:
            return JSONResponse(status_code=400,
                content={"error": "Invalid remedy_style. Must be 'traditional' or 'secular'."})

        updates = {}
        if language:
            updates["language"] = language
        if "remedy_style" in body:
            updates["remedy_style"] = remedy_style

        if not updates:
            return {"status": "ok", "message": "No changes"}

        supabase.table("charts").update(updates).eq("id", chart_id).execute()

        # Clear caches so content regenerates in new language
        if language:
            for table in ["practice_schedule_cache", "welcome_signals", "weekly_briefings", "monthly_deepdives"]:
                try:
                    supabase.table(table).delete().eq("chart_id", chart_id).execute()
                except Exception:
                    pass

        logger.info(f"Preferences updated for {chart_id}: {updates}")
        return {"status": "ok", "updated": updates}

    except Exception as e:
        logger.error(f"update-preferences failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to update preferences"})

'''


def patch_main_py(main_py_path):
    print(f"\n{'='*60}")
    print(f"PATCHING: {main_py_path}")
    print(f"{'='*60}")

    backup(main_py_path)
    content = read_file(main_py_path)
    original = content
    changes = 0

    # ─── Add import ───
    if "from language_utils import" not in content:
        import_line = "\nfrom language_utils import build_language_instruction, resolve_language, resolve_language_from_query\n"

        # Strategy: find the last import-like line
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith("import ") or stripped.startswith("from ") or
                stripped.startswith("try:") or stripped.startswith("except")):
                insert_idx = i

        # Insert after the last import block
        lines.insert(insert_idx + 1, import_line)
        content = "\n".join(lines)
        print(f"  ✓ Added language_utils import after line {insert_idx + 1}")
        changes += 1
    else:
        print("  · language_utils import already present")

    # ─── Add endpoint ───
    if "update-preferences" not in content and "update_preferences" not in content:
        # Strategy: find "if __name__" or end of file
        main_match = re.search(r'\nif\s+__name__\s*==', content)
        if main_match:
            pos = main_match.start()
            content = content[:pos] + UPDATE_PREFS_ENDPOINT + content[pos:]
            print("  ✓ Added update-preferences endpoint (before __main__)")
        else:
            content += UPDATE_PREFS_ENDPOINT
            print("  ✓ Added update-preferences endpoint (appended)")
        changes += 1
    else:
        print("  · update-preferences endpoint already present")

    if changes > 0:
        write_file(main_py_path, content)
        print(f"  ✓ Saved {changes} changes to {main_py_path}")
    else:
        print("  · No changes needed")

    return changes


# ═══════════════════════════════════════════════════════════════════
# PATCH prashna_engine.py
# ═══════════════════════════════════════════════════════════════════

def patch_prashna_engine(prashna_path):
    print(f"\n{'='*60}")
    print(f"PATCHING: {prashna_path}")
    print(f"{'='*60}")

    backup(prashna_path)
    content = read_file(prashna_path)
    changes = 0

    # ─── Add import ───
    if "build_language_instruction" not in content:
        import_block = (
            "\n\n# --- Language Utils (Sprint L) ---\n"
            "try:\n"
            "    from language_utils import build_language_instruction\n"
            "except ImportError:\n"
            '    def build_language_instruction(lang="en"): return ""  # fallback\n'
        )
        # Insert after logger line
        logger_match = re.search(r'^logger\s*=.*$', content, re.MULTILINE)
        if logger_match:
            pos = logger_match.end()
        else:
            # After last import
            for m in re.finditer(r'^(?:from|import)\s+', content, re.MULTILINE):
                pos = m.end()
            pos = content.index("\n", pos)

        content = content[:pos] + import_block + content[pos:]
        print("  ✓ Added language_utils import")
        changes += 1
    else:
        print("  · import already present")

    # ─── Patch build_prashna_prompt signature ───
    old_sig = (
        'def build_prashna_prompt(verdict_data: dict, question: str, '
        'user_name: str = "User",\n'
        '                          locale: str = "global") -> str:'
    )
    new_sig = (
        'def build_prashna_prompt(verdict_data: dict, question: str, '
        'user_name: str = "User",\n'
        '                          locale: str = "global", '
        'language: str = "en") -> str:'
    )

    if old_sig in content:
        content = content.replace(old_sig, new_sig, 1)
        print("  ✓ Added language param to build_prashna_prompt()")
        changes += 1
    elif 'language: str = "en"' in content.split("def build_prashna_prompt")[1].split("\n")[0:3].__repr__() if "def build_prashna_prompt" in content else False:
        print("  · build_prashna_prompt already has language")
    else:
        print("  ⚠ Could not match build_prashna_prompt signature — may need manual edit")

    # ─── Inject language block before return ───
    bpp_match = re.search(r'def build_prashna_prompt\(', content)
    if bpp_match:
        rest = content[bpp_match.start():]
        # Find "    return prompt" in this function
        return_match = re.search(r'^    return prompt\s*$', rest, re.MULTILINE)
        if return_match and "lang_block = build_language_instruction" not in rest[:return_match.start()]:
            abs_pos = bpp_match.start() + return_match.start()
            injection = (
                "    # --- Language injection (Sprint L) ---\n"
                "    lang_block = build_language_instruction(language)\n"
                "    prompt = lang_block + prompt\n\n"
            )
            content = content[:abs_pos] + injection + content[abs_pos:]
            print("  ✓ Injected language block before return in build_prashna_prompt()")
            changes += 1
        else:
            print("  · Language block already in build_prashna_prompt")

    # ─── Patch run_prashna_engine signature ───
    old_rpe = '    locale: str = "global",\n) -> dict:'
    new_rpe = '    locale: str = "global",\n    language: str = "en",\n) -> dict:'

    if old_rpe in content:
        content = content.replace(old_rpe, new_rpe, 1)
        print("  ✓ Added language param to run_prashna_engine()")
        changes += 1
    else:
        print("  · run_prashna_engine signature already patched or different")

    # ─── Pass language in internal call ───
    old_call = (
        '    claude_prompt = build_prashna_prompt(\n'
        '        verdict_data=verdict_data,\n'
        '        question=question,\n'
        '        user_name=user_name,\n'
        '        locale=locale,\n'
        '    )'
    )
    new_call = (
        '    claude_prompt = build_prashna_prompt(\n'
        '        verdict_data=verdict_data,\n'
        '        question=question,\n'
        '        user_name=user_name,\n'
        '        locale=locale,\n'
        '        language=language,\n'
        '    )'
    )

    if old_call in content:
        content = content.replace(old_call, new_call, 1)
        print("  ✓ Added language= to internal build_prashna_prompt() call")
        changes += 1
    else:
        print("  · Internal call already patched or different format")

    if changes > 0:
        write_file(prashna_path, content)
        print(f"  ✓ Saved {changes} changes to {prashna_path}")
    else:
        print("  · No changes needed")

    return changes


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("ANTAR — Language Patch v2 (Auto-Discovery)")
    print("=" * 60)
    print(f"Working directory: {os.getcwd()}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Find files
    main_py = find_file("main.py")
    prashna_py = find_file("prashna_engine.py")

    print(f"\nDiscovered files:")
    print(f"  main.py:           {main_py or '✗ NOT FOUND'}")
    print(f"  prashna_engine.py: {prashna_py or '✗ NOT FOUND'}")

    if not main_py:
        print("\n✗ FATAL: main.py not found. Are you in the project root?")
        print("  Try: cd /path/to/antarai && python 03_apply_language_patch_v2.py")
        return 1

    # Setup language_utils.py
    main_dir = os.path.dirname(main_py) or "."
    print(f"\nSetting up language_utils.py in {main_dir}/")
    setup_language_utils(main_dir)

    # Also copy to antar_engine/ if it exists (for prashna_engine imports)
    engine_dir = os.path.join(main_dir, "antar_engine")
    if os.path.isdir(engine_dir):
        engine_utils = os.path.join(engine_dir, "language_utils.py")
        root_utils = os.path.join(main_dir, "language_utils.py")
        if os.path.exists(root_utils) and not os.path.exists(engine_utils):
            shutil.copy2(root_utils, engine_utils)
            print(f"  ✓ Also copied to {engine_utils}")

    # Patch main.py
    main_changes = patch_main_py(main_py)

    # Patch prashna_engine.py
    prashna_changes = 0
    if prashna_py:
        prashna_changes = patch_prashna_engine(prashna_py)
    else:
        print(f"\n{'='*60}")
        print("SKIPPED: prashna_engine.py not found")
        print("='*60")
        print("  If it's in a subfolder, run:")
        print("  python 03_apply_language_patch_v2.py")
        print("  from the project root where antar_engine/ is visible")

    # Summary
    total = main_changes + prashna_changes
    print(f"\n{'='*60}")
    print(f"SUMMARY: {total} total changes applied")
    print(f"{'='*60}")

    print("""
REMAINING MANUAL STEPS:
═══════════════════════

1. SUPABASE SQL EDITOR — run this:
   ALTER TABLE charts ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en';
   ALTER TABLE charts ADD COLUMN IF NOT EXISTS remedy_style TEXT DEFAULT NULL;

2. MAIN.PY — Wire language into /predict endpoint:
   Find where you call Claude (call_llm or similar).
   BEFORE that call, add:

     from language_utils import build_language_instruction, resolve_language
     body = await request.json()  # or however you parse the request
     chart_row = ...  # your Supabase chart fetch result
     _lang = resolve_language(body, chart_row)
     _lang_block = build_language_instruction(_lang)
     system_prompt = _lang_block + system_prompt  # prepend to existing prompt

3. MAIN.PY — Wire language into /prashna endpoint:
   Find where run_prashna_engine() is called. Add language= :

     _lang = resolve_language(body, chart_row)
     result = run_prashna_engine(..., language=_lang)

4. MAIN.PY — Wire language into /daily-signal, /welcome, /weekly-briefing:
   Same pattern. For GET endpoints use resolve_language_from_query().

5. DEPLOY:
   git add -A
   git commit -m "Sprint L: language preferences + update-preferences endpoint"
   git push

6. TEST (after Railway redeploys):
   chmod +x 04_test_language_macos.sh
   ./04_test_language_macos.sh
""")

    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
