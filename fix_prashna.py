#!/usr/bin/env python3
"""
fix_prashna_emotion.py
======================
Run: python fix_prashna_emotion.py

Fixes the broken E1 emotion injection that split the call_llm() call in half.
"""

import os

MAIN_FILE = "main.py"

# The broken code (lines 4380-4393)
BROKEN = '''        # ─── 5. Call Claude to explain the verdict ───
        explanation = ""
        try:
            result_tuple = await call_llm(
                prompt=question,

        # Append emotional tone to prashna prompt
        _prashna_prompt = engine_result.get("claude_prompt", "")
        if _prashna_emotion_block:
            _prashna_prompt += _prashna_emotion_block

                system_override=_prashna_prompt,
            )'''

# The fixed code
FIXED = '''        # ─── 5. Call Claude to explain the verdict ───
        # Append emotional tone to prashna prompt
        _prashna_prompt = engine_result.get("claude_prompt", "")
        if _prashna_emotion_block:
            _prashna_prompt += _prashna_emotion_block

        explanation = ""
        try:
            result_tuple = await call_llm(
                prompt=question,
                system_override=_prashna_prompt,
            )'''

def fix():
    if not os.path.exists(MAIN_FILE):
        print(f"ERROR: {MAIN_FILE} not found.")
        return

    with open(MAIN_FILE, "r") as f:
        content = f.read()

    if BROKEN in content:
        content = content.replace(BROKEN, FIXED, 1)
        with open(MAIN_FILE, "w") as f:
            f.write(content)
        print("FIXED: Moved emotion block before try/call_llm, restored call_llm() call")
    else:
        print("Pattern not found — checking if already fixed...")
        if "if _prashna_emotion_block:" in content and "system_override=_prashna_prompt," in content:
            # Check if it's in the right order
            emotion_idx = content.find("if _prashna_emotion_block:")
            call_idx = content.find("system_override=_prashna_prompt,")
            if emotion_idx < call_idx:
                print("Already fixed — emotion block is before call_llm.")
            else:
                print("ERROR: Emotion block is after call_llm. Manual fix needed.")
        else:
            print("ERROR: Cannot find the broken pattern. Show lines 4375-4400 for manual fix.")

if __name__ == "__main__":
    print("=" * 50)
    print("FIX PRASHNA EMOTION INJECTION")
    print("=" * 50)
    fix()
    print("=" * 50)
