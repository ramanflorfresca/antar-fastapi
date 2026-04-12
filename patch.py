"""
patch_plain_summary_fix.py — Sprint S3-B1: Fix plain_summary timing inversion

THE BUG:
  plain_english.py's generate_plain_english() makes a second Claude call to compress
  the raw prediction into a structured JSON. The prompt instructions for plain_summary
  tell Claude to write "what is happening right now" — but give no instruction to
  PRESERVE the timing direction from the raw prediction.

  Result: Claude sometimes inverts the signal. If the raw prediction says
  "funding window CLOSES April–July", plain_summary may write
  "your funding window is active now" — the exact opposite.

THE FIX:
  1. Strengthen the plain_summary instruction to explicitly say:
     "MUST preserve the core timing verdict — if the prediction says a window
      is CLOSING or BLOCKED, the summary must say that too. Never reframe
      a warning as an opportunity."

  2. Add a TIMING SIGNAL EXTRACTION step: Claude must first identify the
     timing verdict from the raw prediction (OPEN / CLOSING / BLOCKED / BUILDING)
     and then write the summary consistent with that verdict.

  3. Add a hard contradiction check instruction: "If your plain_summary contradicts
     the timing_window field, you have made an error. Rewrite."

  4. Add a post-parse validation in Python: check if plain_summary contains
     positive framing when timing_window contains friction keywords, and log a warning.

Run: python patch_plain_summary_fix.py
Backs up to: antar_engine/plain_english.py.bak_summary_fix
"""

import os
import re
import shutil

TARGET = "antar_engine/plain_english.py"
BACKUP = TARGET + ".bak_summary_fix"


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found. Run from ~/antarai project root.")
        return False

    shutil.copy2(TARGET, BACKUP)
    print(f"✓ Backed up to {BACKUP}")

    with open(TARGET, "r") as f:
        content = f.read()

    original_content = content
    changes_made = 0

    # ═══════════════════════════════════════════════════════════════
    # PATCH 1: Strengthen the plain_summary instruction in the system prompt
    # ═══════════════════════════════════════════════════════════════

    # The current instruction is:
    #   "plain_summary": "2-3 sentences. What is happening in their life right now. No jargon."
    # OR (after doctor mode patch):
    #   "plain_summary": "2-3 sentences. What is happening in their life right now. No jargon. Lead with the conclusion, not the cause."
    #
    # We replace the plain_summary line in the JSON FORMAT block with a stronger version.

    old_summary_v1 = '"plain_summary": "2-3 sentences. What is happening in their life right now. No jargon."'
    old_summary_v2 = '"plain_summary": "2-3 sentences. What is happening in their life right now. No jargon. Lead with the conclusion, not the cause."'

    new_summary = (
        '"plain_summary": "2-3 sentences. What is happening in their life right now. '
        'CRITICAL: You MUST preserve the core timing verdict from the raw prediction. '
        'If the raw prediction says a window is CLOSING, BLOCKED, or a period of FRICTION, '
        'your summary must say that too — never reframe a warning as an opportunity. '
        'If the raw prediction says a window is OPEN or BUILDING, reflect that. '
        'The summary must AGREE with timing_window. If they contradict, rewrite the summary. '
        'No jargon. Lead with the conclusion."'
    )

    if old_summary_v2 in content:
        content = content.replace(old_summary_v2, new_summary, 1)
        print("✓ Replaced plain_summary instruction (v2 — doctor mode version)")
        changes_made += 1
    elif old_summary_v1 in content:
        content = content.replace(old_summary_v1, new_summary, 1)
        print("✓ Replaced plain_summary instruction (v1 — original version)")
        changes_made += 1
    else:
        # Try a looser match in case formatting differs
        pattern = r'"plain_summary":\s*"2-3 sentences\.[^"]*"'
        match = re.search(pattern, content)
        if match:
            content = content[:match.start()] + new_summary + content[match.end():]
            print("✓ Replaced plain_summary instruction (regex match)")
            changes_made += 1
        else:
            print("⚠ Could not find plain_summary instruction — manual edit needed")
            print("  Look for the JSON FORMAT block in the system prompt")
            print("  Find the plain_summary line and add the CRITICAL timing preservation instruction")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 2: Add TIMING DIRECTION RULE near the other rules
    # ═══════════════════════════════════════════════════════════════

    timing_rule_marker = "TIMING DIRECTION RULE"

    if timing_rule_marker not in content:
        timing_rule = """
TIMING DIRECTION RULE — READ THIS BEFORE WRITING plain_summary:

Step 1: Read the raw prediction and identify the timing verdict.
  - Is the window OPEN/ACTIVE/PEAK? → summary must reflect opportunity
  - Is the window CLOSING/ENDING soon? → summary must convey urgency to act NOW
  - Is the window BLOCKED/FRICTION/AVOID? → summary must convey caution or patience
  - Is the window BUILDING/PREPARING? → summary must reflect momentum not yet arrived

Step 2: Write plain_summary consistent with that verdict.
  WRONG: Raw prediction says "funding window closes April–July" → summary says "your funding energy is active now"
  RIGHT: Raw prediction says "funding window closes April–July" → summary says "the next 3 months are a friction period for raising capital — focus on revenue instead"

  WRONG: Raw prediction says "career peak window through June" → summary says "this is a challenging time for career moves"
  RIGHT: Raw prediction says "career peak window through June" → summary says "your career energy is at peak strength now — this is the window to move"

Step 3: Check timing_window field. If plain_summary contradicts it, rewrite plain_summary.

"""
        # Find the best insertion point — just before "TASK:" or "FORMAT —" in the system prompt
        # Try to insert before the FORMAT block
        insert_markers = ["FORMAT —", "FORMAT:", "TASK:", "You must return EXACTLY"]
        inserted = False
        for marker in insert_markers:
            idx = content.find(marker)
            if idx > 0:
                # Check we're inside the system prompt string (between quotes or triple quotes)
                content = content[:idx] + timing_rule + content[idx:]
                print(f"✓ Added TIMING DIRECTION RULE before '{marker}'")
                changes_made += 1
                inserted = True
                break

        if not inserted:
            print("⚠ Could not find insertion point for TIMING DIRECTION RULE")
            print("  Manually add this rule to the system prompt in generate_plain_english()")
            print("  before the FORMAT / TASK section:")
            print(timing_rule)
    else:
        print("⊘ TIMING DIRECTION RULE already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 3: Add Python-level contradiction check after parsing
    # ═══════════════════════════════════════════════════════════════

    contradiction_marker = "# --- TIMING CONTRADICTION CHECK ---"

    if contradiction_marker not in content:
        contradiction_check = '''
    # --- TIMING CONTRADICTION CHECK ---
    # Detect if plain_summary contradicts timing_window and log a warning
    try:
        _summary = result.get("plain_summary", "").lower()
        _timing = result.get("timing_window", "").lower()
        _friction_words = {"close", "closing", "block", "blocked", "friction", "avoid",
                           "caution", "wait", "delay", "difficult", "challenging", "not now"}
        _positive_words = {"strong", "peak", "active", "open", "opportunity", "best time",
                           "favorable", "window is open", "act now", "move now"}
        _timing_has_friction = any(w in _timing for w in _friction_words)
        _summary_has_positive = any(w in _summary for w in _positive_words)
        _timing_has_positive = any(w in _timing for w in _positive_words)
        _summary_has_friction = any(w in _summary for w in _friction_words)
        if _timing_has_friction and _summary_has_positive:
            import logging
            logging.getLogger("plain_english").warning(
                f"TIMING CONTRADICTION DETECTED: timing_window='{result.get('timing_window')}' "
                f"but plain_summary has positive framing. Chart may receive wrong signal. "
                f"Summary: '{result.get('plain_summary', '')[:100]}'"
            )
        elif _timing_has_positive and _summary_has_friction:
            import logging
            logging.getLogger("plain_english").warning(
                f"TIMING CONTRADICTION DETECTED: timing_window='{result.get('timing_window')}' "
                f"but plain_summary has friction framing. "
                f"Summary: '{result.get('plain_summary', '')[:100]}'"
            )
    except Exception:
        pass  # Never crash the prediction over a logging check
    # --- END TIMING CONTRADICTION CHECK ---
'''
        # Find where the result dict is returned from generate_plain_english
        # Look for "return result" or "return pe" or "return {"
        # Insert the check BEFORE the return statement

        return_patterns = [
            r"(\n\s+return\s+result\s*\n)",
            r"(\n\s+return\s+pe\s*\n)",
            r"(\n\s+return\s+\{\s*\n)",
            r"(\n\s+return\s+parsed\s*\n)",
            r"(\n\s+return\s+data\s*\n)",
        ]

        inserted = False
        for pattern in return_patterns:
            match = re.search(pattern, content)
            if match:
                insert_pos = match.start()
                content = content[:insert_pos] + "\n" + contradiction_check + content[insert_pos:]
                print("✓ Added Python-level timing contradiction check before return")
                changes_made += 1
                inserted = True
                break

        if not inserted:
            # Try a simpler approach — find the last return in generate_plain_english
            # by looking for the function and finding its return
            fn_match = re.search(r"async\s+def\s+generate_plain_english", content)
            if fn_match:
                fn_start = fn_match.start()
                # Find the last return after the function definition
                returns = list(re.finditer(r"\n(\s+)return\s+", content[fn_start:]))
                if returns:
                    last_return = returns[-1]
                    insert_pos = fn_start + last_return.start()
                    content = content[:insert_pos] + "\n" + contradiction_check + content[insert_pos:]
                    print("✓ Added timing contradiction check (last return in function)")
                    changes_made += 1
                    inserted = True

            if not inserted:
                print("⚠ Could not auto-insert contradiction check")
                print("  Manually add the following block before the 'return result' in generate_plain_english():")
                print(contradiction_check)
    else:
        print("⊘ Timing contradiction check already exists")

    # ═══════════════════════════════════════════════════════════════
    # WRITE or ABORT
    # ═══════════════════════════════════════════════════════════════

    if changes_made == 0:
        print("\n⚠ No changes were applied automatically.")
        print("  The file structure may differ from expected.")
        print("  See MANUAL EDITS NEEDED below.")
        print_manual_instructions()
        return False

    with open(TARGET, "w") as f:
        f.write(content)

    print(f"\n✓ {changes_made} change(s) applied to {TARGET}")
    print(f"  Backup saved to {BACKUP}")
    print(f"\n  NEXT STEPS:")
    print(f"  1. Review the patch: diff {BACKUP} {TARGET}")
    print(f"  2. Check syntax: python3 -c \"import ast; ast.parse(open('{TARGET}').read()); print('Syntax OK')\"")
    print(f"  3. Deploy: git add -A && git commit -m 'fix: plain_summary timing inversion bug (S3-B1)' && git push")
    print(f"  4. Test: curl POST /api/v1/predict with chart_id de02bb52...")
    print(f"     Compare plain_summary vs timing_window — they must agree on direction")
    print(f"  5. Watch Railway logs for 'TIMING CONTRADICTION DETECTED' warnings")
    print(f"     If you see them after deploy, the bug persists in edge cases")

    return True


def print_manual_instructions():
    """Print what to do if auto-patch fails."""
    print("""
═══════════════════════════════════════════════════════════════
MANUAL EDIT INSTRUCTIONS (if auto-patch failed)
═══════════════════════════════════════════════════════════════

Open: antar_engine/plain_english.py

EDIT 1 — Find the plain_summary line in the FORMAT block (inside the system prompt).
It currently says something like:
  "plain_summary": "2-3 sentences. What is happening in their life right now. No jargon."

Replace with:
  "plain_summary": "2-3 sentences. What is happening in their life right now.
  CRITICAL: You MUST preserve the core timing verdict from the raw prediction.
  If the raw prediction says a window is CLOSING, BLOCKED, or a period of FRICTION,
  your summary must say that too — never reframe a warning as an opportunity.
  If the raw prediction says a window is OPEN or BUILDING, reflect that.
  The summary must AGREE with timing_window. If they contradict, rewrite. No jargon."

EDIT 2 — Find the system prompt string (the long string passed as "content" to the
Claude API call in generate_plain_english). Before the FORMAT or TASK section, add:

  TIMING DIRECTION RULE:
  Before writing plain_summary, identify whether the raw prediction's timing is:
  OPEN/ACTIVE → summary reflects opportunity
  CLOSING/ENDING → summary conveys urgency to act now or that window is closing
  BLOCKED/FRICTION → summary conveys caution or patience required
  BUILDING → summary reflects momentum not yet arrived
  Then write plain_summary consistent with that direction.
  plain_summary must NEVER contradict timing_window.

EDIT 3 — Find the return statement at the end of generate_plain_english() and add
this Python check just before it:

  # Timing contradiction check
  try:
      _summary = result.get("plain_summary", "").lower()
      _timing = result.get("timing_window", "").lower()
      if any(w in _timing for w in ["close","block","friction","avoid"]) and \\
         any(w in _summary for w in ["strong","peak","active","open","opportunity"]):
          import logging
          logging.getLogger("plain_english").warning(
              f"TIMING CONTRADICTION: timing={result.get('timing_window')} "
              f"but summary has positive framing: {result.get('plain_summary','')[:80]}"
          )
  except Exception:
      pass

═══════════════════════════════════════════════════════════════
""")


def verify_patch():
    """Quick check that the key strings are present after patching."""
    if not os.path.exists(TARGET):
        print("ERROR: Target file not found")
        return

    with open(TARGET, "r") as f:
        content = f.read()

    checks = [
        ("CRITICAL: You MUST preserve the core timing verdict", "plain_summary instruction strengthened"),
        ("TIMING DIRECTION RULE", "timing direction rule added"),
        ("TIMING CONTRADICTION CHECK", "contradiction check added"),
    ]

    print("\n── Verification ──")
    all_pass = True
    for check_str, label in checks:
        found = check_str in content
        status = "✓" if found else "✗"
        print(f"  {status} {label}")
        if not found:
            all_pass = False

    # Syntax check
    try:
        import ast
        ast.parse(content)
        print("  ✓ Python syntax valid")
    except SyntaxError as e:
        print(f"  ✗ SYNTAX ERROR: {e}")
        print(f"    Run: python3 -c \"import ast; ast.parse(open('{TARGET}').read())\"")
        all_pass = False

    if all_pass:
        print("\n✓ All checks passed. Ready to deploy.")
    else:
        print(f"\n⚠ Some checks failed. Review {TARGET} before deploying.")
        print(f"  Backup is at {BACKUP} if you need to restore.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_patch()
    else:
        success = patch()
        if success:
            verify_patch()
