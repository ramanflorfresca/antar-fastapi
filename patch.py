#!/usr/bin/env python3
"""
patch_practice_lang_v2.py
Targeted fix: translates _sched before both return points in get_practice_schedule_endpoint.
Run from ~/antarai: python patch_practice_lang_v2.py
"""
import shutil, os, ast

TARGET = os.path.expanduser("~/antarai/main.py")
BACKUP = TARGET + ".bak_practice_lang_v2"
shutil.copy2(TARGET, BACKUP)

with open(TARGET, "r") as f:
    src = f.read()

# Verify translation function is present (from previous patch attempt)
if "_translate_practice_schedule_es" not in src:
    print("ERROR: _translate_practice_schedule_es not found in main.py")
    print("The translation function was lost in the revert.")
    print("Need to re-inject it.")
    exit(1)
else:
    print("Translation function present - good")

# Patch the two return lines precisely
OLD_CACHE_RETURN = '        return {"status": "ok", "source": "cache", "schedule": _sched}'
NEW_CACHE_RETURN = '        if language == "es": _sched = _translate_practice_schedule_es(_sched)\n        return {"status": "ok", "source": "cache", "schedule": _sched}'

OLD_GEN_RETURN = '        return {"status": "ok", "source": "generated", "schedule": _sched}'
NEW_GEN_RETURN = '        if language == "es": _sched = _translate_practice_schedule_es(_sched)\n        return {"status": "ok", "source": "generated", "schedule": _sched}'

patched = 0
if OLD_CACHE_RETURN in src:
    src = src.replace(OLD_CACHE_RETURN, NEW_CACHE_RETURN)
    print("Patched cache return")
    patched += 1
else:
    print("WARNING: cache return not found")

if OLD_GEN_RETURN in src:
    src = src.replace(OLD_GEN_RETURN, NEW_GEN_RETURN)
    print("Patched generated return")
    patched += 1
else:
    print("WARNING: generated return not found")

if patched == 0:
    print("ERROR: Neither return found. Check main.py manually.")
    exit(1)

with open(TARGET, "w") as f:
    f.write(src)

try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    shutil.copy2(BACKUP, TARGET)
    print("Backup restored")
    exit(1)

print(f"\nPatched {patched}/2 return points. Deploy:")
print("  git add -A && git commit -m 'feat: Spanish translation for practice schedule' && git push")
