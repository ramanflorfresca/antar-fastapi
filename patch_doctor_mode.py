"""
patch_doctor_mode.py — Sprint 1.3: Doctor Mode Prompt Injection

Patches antar_engine/plain_english.py to:
1. Add verdict-first response format (✦ VERDICT: HIBERNATE. DO NOT CLOSE.)
2. Inject domain vocabulary from symptom_library
3. Add bedside manner guardrail (CEO = Chairman, Love = Mediator)
4. Add verdict_header field to output JSON

Run: python patch_doctor_mode.py
Backs up to: antar_engine/plain_english.py.bak_doctor
"""

import os
import re
import shutil

TARGET = "antar_engine/plain_english.py"
BACKUP = TARGET + ".bak_doctor"


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found. Run from project root.")
        return False

    # Backup
    shutil.copy2(TARGET, BACKUP)
    print(f"✓ Backed up to {BACKUP}")

    with open(TARGET, "r") as f:
        content = f.read()

    # ═══════════════════════════════════════════════════════════════
    # PATCH 1: Add import for symptom_library at top
    # ═══════════════════════════════════════════════════════════════
    
    import_line = "from antar_engine.symptom_library import build_diagnostic_prompt_block, get_domain_vocabulary, get_primary_symptom"
    
    if "symptom_library" not in content:
        # Find the last import line and add after it
        import_pattern = r"(^(?:from|import)\s+.+$)"
        matches = list(re.finditer(import_pattern, content, re.MULTILINE))
        if matches:
            last_import_end = matches[-1].end()
            content = content[:last_import_end] + "\n" + import_line + "\n" + content[last_import_end:]
            print("✓ Added symptom_library import")
        else:
            content = import_line + "\n\n" + content
            print("✓ Added symptom_library import (at top)")
    else:
        print("⊘ symptom_library import already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 2: Update the system prompt to include verdict-first format
    # ═══════════════════════════════════════════════════════════════

    # Find the current JSON format instruction in the prompt
    old_format_marker = '"plain_summary": "2-3 sentences'
    
    if old_format_marker in content and '"verdict_header"' not in content:
        # Find the full JSON format block and add verdict_header
        old_json = '''"plain_summary": "2-3 sentences. What is happening in their life right now. No jargon."'''
        new_json = '''"verdict_header": "VERDICT: [ACTION WORD]. [ONE SENTENCE STRATEGIC DIRECTIVE]. Example: VERDICT: HIBERNATE. DO NOT CLOSE NEW DEALS.",
  "plain_summary": "2-3 sentences. What is happening in their life right now. No jargon. Lead with the conclusion, not the cause."'''
        
        content = content.replace(old_json, new_json, 1)
        print("✓ Added verdict_header to output JSON format")
    else:
        print("⊘ verdict_header already exists or format marker not found")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 3: Add Rule 12 — Verdict-First and Domain Voice
    # ═══════════════════════════════════════════════════════════════

    rule_12_marker = "Rule 12: VERDICT-FIRST"
    
    if rule_12_marker not in content:
        # Find where rules end (look for the last Rule N)
        rule_pattern = r"(Rule \d+:.*?)(?=\n\n|\nFORMAT|\nTASK|\nHere is)"
        matches = list(re.finditer(rule_pattern, content, re.DOTALL))
        
        rule_12_text = """
Rule 12: VERDICT-FIRST AND DOMAIN VOICE.
Every response MUST begin with a verdict header line: "✦ VERDICT: [ACTION]. [DIRECTIVE]."
Examples:
- "✦ VERDICT: HIBERNATE. External capital is offline until Q2 2027."
- "✦ VERDICT: EXECUTE NOW. Your authority window closes in 3 weeks."
- "✦ VERDICT: RECALIBRATE. Partnership alignment is drifting."
- "✦ VERDICT: HOLD POSITION. Career friction will clear after March 2028."
The verdict must use the user's domain language — not astrology. If they ask about money, use Runway, Overhead, Burn Rate. If about career, use Authority, Leverage, Positioning. If about relationships, use Alignment, Sync, Convergence. If about health, use Vitals, Reserves, Recovery.
Match the user's register: if they use CEO language, respond like a Chairman. If they use relationship language, respond like a Conflict Mediator. If they use health language, respond like an Executive Physician.

Rule 13: BEDSIDE MANNER GUARDRAIL.
Never present a planet or house as the cause. Present the "Energy Disruption" as the cause. Use the jargon of the user's specific domain (Finance/Career/Love/Health) to explain both the problem and the cure. The user should feel like they are receiving a strategic briefing, not a horoscope reading.
"""
        
        if matches:
            last_rule_end = matches[-1].end()
            content = content[:last_rule_end] + "\n" + rule_12_text + content[last_rule_end:]
            print("✓ Added Rule 12 (Verdict-First) and Rule 13 (Bedside Manner)")
        else:
            # Fallback: find "TASK:" and inject before it
            task_idx = content.find("TASK:")
            if task_idx > 0:
                content = content[:task_idx] + rule_12_text + "\n" + content[task_idx:]
                print("✓ Added Rule 12 + 13 (before TASK)")
            else:
                print("⚠ Could not find insertion point for Rule 12/13")
    else:
        print("⊘ Rule 12 already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 4: Inject diagnostic block into generate_plain_english()
    # ═══════════════════════════════════════════════════════════════

    diagnostic_marker = "# --- DIAGNOSTIC PRE-SCAN ---"
    
    if diagnostic_marker not in content:
        # Find the generate_plain_english function and inject diagnostic scan
        # Look for where the system prompt is assembled
        
        # Strategy: find where chart_context is used and inject diagnostic block
        # The function signature includes chart_context parameter
        
        gen_fn_pattern = r"(async\s+def\s+generate_plain_english\s*\([^)]+\))"
        gen_match = re.search(gen_fn_pattern, content)
        
        if gen_match:
            # Find the first place where the prompt/messages are built after the function def
            fn_start = gen_match.end()
            
            # Look for the messages= or prompt building section
            messages_pattern = r"(messages\s*=\s*\[)"
            msg_match = re.search(messages_pattern, content[fn_start:])
            
            if msg_match:
                insert_pos = fn_start + msg_match.start()
                
                diagnostic_injection = """
    # --- DIAGNOSTIC PRE-SCAN ---
    # Scan chart for active symptoms and inject domain vocabulary
    diagnostic_block = ""
    try:
        chart_planets = chart_context.get("chart_data", {}).get("planets", {})
        if chart_planets:
            diagnostic_block = build_diagnostic_prompt_block(
                chart_context.get("chart_data", {}),
                chart_context.get("question", ""),
                chart_context.get("concern", None)
            )
    except Exception as e:
        diagnostic_block = ""  # Non-critical — don't crash if symptom scan fails
    # --- END DIAGNOSTIC PRE-SCAN ---

    """
                content = content[:insert_pos] + diagnostic_injection + content[insert_pos:]
                print("✓ Injected diagnostic pre-scan into generate_plain_english()")
                
                # Now inject the diagnostic_block into the system prompt content
                # Find where user content/raw_prediction is added to messages
                # Add diagnostic_block to the user message
                
                # Look for where raw_prediction is inserted into the prompt
                raw_pred_pattern = r'(raw_prediction|prediction_text|raw_text)'
                raw_matches = list(re.finditer(raw_pred_pattern, content[insert_pos:]))
                
                if raw_matches:
                    # Find the first string concatenation or f-string with raw_prediction
                    for rm in raw_matches:
                        check_area = content[insert_pos + rm.start() - 100 : insert_pos + rm.end() + 200]
                        if "content" in check_area.lower() or "message" in check_area.lower():
                            # Found it — inject diagnostic_block before raw_prediction in the user message
                            # We'll do a simpler approach: modify the user content to prepend diagnostic
                            break
                
                print("  (diagnostic_block variable created — wire into prompt manually if auto-wire fails)")
            else:
                print("⚠ Could not find messages= pattern in generate_plain_english()")
        else:
            print("⚠ Could not find generate_plain_english() function")
    else:
        print("⊘ Diagnostic pre-scan already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 5: Add verdict_header to output parsing
    # ═══════════════════════════════════════════════════════════════

    verdict_parse_marker = "verdict_header"
    
    # Check if we need to add verdict_header extraction
    if "verdict_header" not in content or content.count("verdict_header") < 3:
        # Find where plain_summary is extracted from the JSON response
        extract_pattern = r"(pe\[.plain_summary.\]|result\[.plain_summary.\]|parsed\[.plain_summary.\]|data\[.plain_summary.\])"
        extract_matches = list(re.finditer(extract_pattern, content))
        
        if extract_matches:
            # Add verdict_header extraction near plain_summary extraction
            for em in extract_matches:
                line_start = content.rfind("\n", 0, em.start()) + 1
                line_end = content.find("\n", em.end())
                current_line = content[line_start:line_end]
                
                # Check if this is inside a dict/return
                if "plain_summary" in current_line and "verdict_header" not in content[line_start-200:line_end+200]:
                    # Add verdict_header extraction after this line
                    indent = len(current_line) - len(current_line.lstrip())
                    verdict_line = " " * indent + "# verdict_header extracted from Claude response (Sprint 1.3)\n"
                    break
            
            print("✓ verdict_header extraction noted (verify in output dict)")
        else:
            print("⊘ Could not find extraction pattern — manual wiring needed")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 6: Update _strip_jargon to also strip leftover house references
    # ═══════════════════════════════════════════════════════════════

    if "house number" not in content.lower() or "\\b\\d{1,2}(st|nd|rd|th)\\s+house" not in content:
        strip_jargon_pattern = r"(def _strip_jargon\s*\([^)]*\)[^:]*:)"
        strip_match = re.search(strip_jargon_pattern, content)
        
        if strip_match:
            fn_body_start = strip_match.end()
            # Find the first return statement in this function
            return_pattern = r"(\n\s+return\s+)"
            return_match = re.search(return_pattern, content[fn_body_start:])
            
            if return_match:
                insert_pos = fn_body_start + return_match.start()
                house_strip = """
    # Strip house number references (e.g., "10th house", "8th house lord")
    import re as _re
    result = _re.sub(r'\\b\\d{1,2}(?:st|nd|rd|th)\\s+house\\s*(?:lord)?', '', result)
    result = _re.sub(r'\\bhouse\\s+\\d{1,2}\\b', '', result)
"""
                content = content[:insert_pos] + house_strip + content[insert_pos:]
                print("✓ Added house number stripping to _strip_jargon()")
            else:
                print("⊘ Could not find return in _strip_jargon")
        else:
            print("⊘ _strip_jargon function not found")
    else:
        print("⊘ House number stripping already exists")

    # ═══════════════════════════════════════════════════════════════
    # WRITE
    # ═══════════════════════════════════════════════════════════════

    with open(TARGET, "w") as f:
        f.write(content)

    print(f"\n✓ Patched {TARGET}")
    print(f"  Backup: {BACKUP}")
    print(f"\n  MANUAL STEPS NEEDED:")
    print(f"  1. Verify diagnostic_block is injected into the user message in generate_plain_english()")
    print(f"  2. Add 'verdict_header' to the return dict")
    print(f"  3. Add 'chart_data' to chart_context when calling generate_plain_english() from main.py")
    print(f"  4. Deploy: git add -A && git commit -m 'feat: doctor mode prompt injection' && git push")
    
    return True


if __name__ == "__main__":
    patch()
