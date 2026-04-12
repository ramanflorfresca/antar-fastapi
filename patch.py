"""
patch_practice_why_duration.py — Sprint S6: Practice Engine Enhancement

WHAT THIS PATCHES:
  antar_engine/practice_engine.py

THREE FIXES:

1. JSONB KEY FALLBACKS — sleeping_planets and rin_debts are stored under
   the 'advanced' key in lal_kitab_data but the engine looks at top level.
   Adds fallback: lk.get("advanced", {}).get("sleeping_planets") etc.

2. frequency_hz — Add frequency_hz to primary_practice and mantra_of_the_day
   dicts so frontend doesn't fall back to hardcoded values.

3. WHY + DURATION fields — Add practice_why, duration_days, duration_label,
   best_day, best_time, completion_milestone to primary_practice dict.
   Add mantra_why, mantra_duration_label, mantra_best_time to mantra dict.
   These power the WHY expansion card in the frontend.

Run: python patch_practice_why_duration.py
Backs up to: antar_engine/practice_engine.py.bak_why_duration
"""

import os
import re
import shutil

TARGET = "antar_engine/practice_engine.py"
BACKUP = TARGET + ".bak_why_duration"

# Planet frequency map (Hz) for Web Audio API
PLANET_FREQUENCIES = {
    "Sun":     126.22,
    "Moon":    210.42,
    "Mars":    144.72,
    "Mercury": 141.27,
    "Jupiter": 183.58,
    "Venus":   221.23,
    "Saturn":  147.85,
    "Rahu":    170.00,
    "Ketu":    136.10,
}

# WHY explanations per planet — plain English, no jargon
PLANET_WHY = {
    "Sun": {
        "why": "Your identity and confidence energy needs strengthening right now. This practice directly activates your leadership capacity.",
        "why_science": "Consistent morning sun exposure regulates cortisol rhythms, which directly affects confidence, decision-making clarity, and executive presence.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "21 days is the minimum cycle for neurological habit formation and measurable energy shift.",
        "best_day": "Sunday",
        "best_time": "Sunrise, facing east",
        "completion_milestone": "Watch for: increased clarity in decisions, others responding to you with more respect.",
    },
    "Moon": {
        "why": "Your emotional processing and intuition channel is overloaded. This practice clears the backlog so your instincts work clearly again.",
        "why_science": "Rhythmic breathing and water-based practices activate the parasympathetic nervous system, reducing cortisol and improving emotional regulation.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "Emotional patterns shift on 21-day cycles aligned with lunar rhythm.",
        "best_day": "Monday",
        "best_time": "Evening, before sleep",
        "completion_milestone": "Watch for: better sleep, clearer emotional responses, reduced reactivity.",
    },
    "Mars": {
        "why": "Your execution and initiative energy is either blocked or misdirected. This practice channels it productively.",
        "why_science": "Physical movement and structured challenge release stored adrenaline and build the neural pathways for decisive action.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "Motor patterns and action habits require 21 days of consistent reinforcement.",
        "best_day": "Tuesday",
        "best_time": "Morning, before 10am",
        "completion_milestone": "Watch for: less procrastination, faster decisions, physical energy increasing.",
    },
    "Mercury": {
        "why": "Your communication and analytical clarity is foggy right now. This practice sharpens it.",
        "why_science": "Writing and structured verbal practice strengthen prefrontal cortex connections, improving working memory and articulation.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "Cognitive clarity builds in 3-week cycles of consistent practice.",
        "best_day": "Wednesday",
        "best_time": "Before 10am",
        "completion_milestone": "Watch for: ideas flowing more easily, conversations landing better, writing feeling clearer.",
    },
    "Jupiter": {
        "why": "Your growth, wisdom and opportunity-recognition channel needs activation. This opens it.",
        "why_science": "Gratitude and generosity practices activate the reward system in ways that broaden cognitive scope — literally helping you see more options.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "Perspective shifts require 21 days of consistent reframing practice.",
        "best_day": "Thursday",
        "best_time": "Morning",
        "completion_milestone": "Watch for: new opportunities appearing, people offering help unprompted, feeling more optimistic.",
    },
    "Venus": {
        "why": "Your relationship and collaboration energy needs harmonising. This practice restores it.",
        "why_science": "Aesthetic and sensory practices activate the ventral vagal system — the biological basis for safe social connection and trust.",
        "duration_days": 21,
        "duration_label": "21 days",
        "duration_reason": "Relationship patterns shift on 21-day cycles of consistent practice.",
        "best_day": "Friday",
        "best_time": "Evening",
        "completion_milestone": "Watch for: relationships feeling less effortful, creative energy returning, financial flow improving.",
    },
    "Saturn": {
        "why": "Your discipline, structure and long-term focus energy is under pressure. This practice stabilises it.",
        "why_science": "Service and structured discipline practices activate delayed-reward circuits — the biological basis for long-term planning and resilience.",
        "duration_days": 40,
        "duration_label": "40 days",
        "duration_reason": "Saturn patterns operate on longer cycles. 40 days is the traditional threshold for structural habit change.",
        "best_day": "Saturday",
        "best_time": "Early morning, before sunrise",
        "completion_milestone": "Watch for: less resistance to difficult tasks, structures in life feeling more stable, long-term clarity improving.",
    },
    "Rahu": {
        "why": "Your amplification and ambition energy is either stuck or overdriving. This practice channels it toward real growth.",
        "why_science": "Novelty-seeking with structured outcomes activates dopamine pathways productively rather than through compulsive behaviour.",
        "duration_days": 18,
        "duration_label": "18 days",
        "duration_reason": "Rahu operates on 18-year cycles. 18 days activates the micro-cycle within it.",
        "best_day": "Saturday",
        "best_time": "Dusk",
        "completion_milestone": "Watch for: obsessive thoughts reducing, clearer ambition direction, less distraction.",
    },
    "Ketu": {
        "why": "Your detachment, intuition and past-pattern release channel needs clearing. This practice completes old cycles.",
        "why_science": "Meditation and release practices activate the default mode network — the brain's system for integrating past experience and releasing what's no longer needed.",
        "duration_days": 18,
        "duration_label": "18 days",
        "duration_reason": "Ketu patterns release on 18-day micro-cycles.",
        "best_day": "Tuesday or Saturday",
        "best_time": "Before sleep",
        "completion_milestone": "Watch for: old anxieties losing their grip, spiritual clarity increasing, less attachment to outcomes.",
    },
}


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found. Run from ~/antarai project root.")
        return False

    shutil.copy2(TARGET, BACKUP)
    print(f"✓ Backed up to {BACKUP}")

    with open(TARGET, "r") as f:
        content = f.read()

    changes_made = 0

    # ═══════════════════════════════════════════════════════════════
    # PATCH 1: Add PLANET_FREQUENCIES and PLANET_WHY dicts at top of file
    # ═══════════════════════════════════════════════════════════════

    if "PLANET_FREQUENCIES" not in content:
        freq_block = '''
# ─── Planet Frequencies (Hz) for Web Audio API ───────────────────────────────
PLANET_FREQUENCIES = {
    "Sun": 126.22, "Moon": 210.42, "Mars": 144.72, "Mercury": 141.27,
    "Jupiter": 183.58, "Venus": 221.23, "Saturn": 147.85,
    "Rahu": 170.00, "Ketu": 136.10,
}

# ─── Planet WHY explanations (plain English) ─────────────────────────────────
PLANET_WHY = {
    "Sun":     {"why": "Your identity and confidence energy needs strengthening right now.",
                "why_science": "Morning sun exposure regulates cortisol, directly affecting confidence and decision clarity.",
                "duration_days": 21, "duration_label": "21 days",
                "duration_reason": "21 days is the minimum for neurological habit formation.",
                "best_day": "Sunday", "best_time": "Sunrise, facing east",
                "completion_milestone": "Watch for: clearer decisions, others responding with more respect."},
    "Moon":    {"why": "Your emotional processing channel is overloaded. This clears the backlog.",
                "why_science": "Breathing and water practices activate the parasympathetic nervous system.",
                "duration_days": 21, "duration_label": "21 days",
                "duration_reason": "Emotional patterns shift on 21-day lunar-aligned cycles.",
                "best_day": "Monday", "best_time": "Evening, before sleep",
                "completion_milestone": "Watch for: better sleep, clearer emotional responses."},
    "Mars":    {"why": "Your execution energy is blocked or misdirected. This channels it productively.",
                "why_science": "Physical movement releases stored adrenaline and builds decisive action pathways.",
                "duration_days": 21, "duration_label": "21 days",
                "duration_reason": "Action habits require 21 days of consistent reinforcement.",
                "best_day": "Tuesday", "best_time": "Morning, before 10am",
                "completion_milestone": "Watch for: less procrastination, faster decisions."},
    "Mercury": {"why": "Your communication and analytical clarity is foggy. This sharpens it.",
                "why_science": "Writing and verbal practice strengthen prefrontal connections, improving articulation.",
                "duration_days": 21, "duration_label": "21 days",
                "duration_reason": "Cognitive clarity builds in 3-week cycles.",
                "best_day": "Wednesday", "best_time": "Before 10am",
                "completion_milestone": "Watch for: ideas flowing more easily, conversations landing better."},
    "Jupiter": {"why": "Your growth and opportunity-recognition channel needs activation.",
                "why_science": "Gratitude practices broaden cognitive scope — literally helping you see more options.",
                "duration_days": 21, "duration_label": "21 days",
                "duration_reason": "Perspective shifts require 21 days of consistent reframing.",
                "best_day": "Thursday", "best_time": "Morning",
                "completion_milestone": "Watch for: new opportunities appearing, people offering help unprompted."},
    "Venus":   {"why": "Your relationship and collaboration energy needs harmonising.",
                "why_science": "Aesthetic practices activate the ventral vagal system — the basis for safe social connection.",
                "duration_days": 21, "duration_label": "21 days",
                "duration_reason": "Relationship patterns shift on 21-day cycles.",
                "best_day": "Friday", "best_time": "Evening",
                "completion_milestone": "Watch for: relationships feeling less effortful, creative energy returning."},
    "Saturn":  {"why": "Your discipline and long-term focus energy is under pressure. This stabilises it.",
                "why_science": "Service practices activate delayed-reward circuits — the basis for resilience.",
                "duration_days": 40, "duration_label": "40 days",
                "duration_reason": "Saturn patterns require 40 days for structural habit change.",
                "best_day": "Saturday", "best_time": "Early morning, before sunrise",
                "completion_milestone": "Watch for: less resistance to difficult tasks, structures feeling more stable."},
    "Rahu":    {"why": "Your amplification energy is stuck or overdriving. This channels it toward real growth.",
                "why_science": "Novelty-seeking with structure activates dopamine pathways productively.",
                "duration_days": 18, "duration_label": "18 days",
                "duration_reason": "Rahu operates on 18-year cycles. 18 days activates the micro-cycle.",
                "best_day": "Saturday", "best_time": "Dusk",
                "completion_milestone": "Watch for: obsessive thoughts reducing, clearer ambition direction."},
    "Ketu":    {"why": "Your intuition and past-pattern release channel needs clearing.",
                "why_science": "Meditation activates the default mode network for integrating and releasing past experience.",
                "duration_days": 18, "duration_label": "18 days",
                "duration_reason": "Ketu patterns release on 18-day micro-cycles.",
                "best_day": "Tuesday or Saturday", "best_time": "Before sleep",
                "completion_milestone": "Watch for: old anxieties losing grip, less attachment to outcomes."},
}

'''
        # Insert after the last import line
        import_pattern = r"(^(?:from|import)\s+.+$)"
        matches = list(re.finditer(import_pattern, content, re.MULTILINE))
        if matches:
            insert_pos = matches[-1].end()
            content = content[:insert_pos] + "\n" + freq_block + content[insert_pos:]
            print("✓ Added PLANET_FREQUENCIES and PLANET_WHY dicts")
            changes_made += 1
        else:
            content = freq_block + content
            print("✓ Added PLANET_FREQUENCIES and PLANET_WHY dicts (at top)")
            changes_made += 1
    else:
        print("⊘ PLANET_FREQUENCIES already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 2: Add frequency_hz to primary_practice dict
    # ═══════════════════════════════════════════════════════════════

    if '"frequency_hz"' not in content and "'frequency_hz'" not in content:
        # Find where primary_practice dict is built — look for convergence_score key
        # which is always in the primary_practice dict
        patterns_to_find = [
            '"convergence_score": ',
            "'convergence_score': ",
        ]
        for p in patterns_to_find:
            idx = content.find(p)
            if idx > 0:
                # Find the end of this key-value line
                line_end = content.find("\n", idx)
                # Add frequency_hz after convergence_score line
                freq_addition = '\n            "frequency_hz": PLANET_FREQUENCIES.get(planet, 136.10),'
                content = content[:line_end] + freq_addition + content[line_end:]
                print("✓ Added frequency_hz to primary_practice dict")
                changes_made += 1
                break
        else:
            print("⚠ Could not find convergence_score in primary_practice dict")
            print("  Manually add: '\"frequency_hz\": PLANET_FREQUENCIES.get(planet, 136.10)'")
    else:
        print("⊘ frequency_hz already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 3: Add frequency_hz to mantra_of_the_day dict
    # ═══════════════════════════════════════════════════════════════

    # Find mantra_of_the_day dict — look for mantra_text key
    mantra_freq_marker = "mantra_of_the_day"
    if mantra_freq_marker in content:
        # Find "count": in the mantra dict context
        mantra_idx = content.find(mantra_freq_marker)
        count_idx = content.find('"count":', mantra_idx)
        if count_idx > 0 and count_idx - mantra_idx < 2000:
            line_end = content.find("\n", count_idx)
            if "frequency_hz" not in content[mantra_idx:mantra_idx + 2000]:
                freq_line = '\n            "frequency_hz": PLANET_FREQUENCIES.get(planet, 136.10),'
                content = content[:line_end] + freq_line + content[line_end:]
                print("✓ Added frequency_hz to mantra_of_the_day dict")
                changes_made += 1
            else:
                print("⊘ mantra frequency_hz already exists")
        else:
            print("⚠ Could not find 'count' in mantra_of_the_day context")
    else:
        print("⚠ mantra_of_the_day not found in file")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 4: Add WHY + duration fields to primary_practice dict
    # ═══════════════════════════════════════════════════════════════

    if "practice_why" not in content:
        # Find the primary_practice dict assembly — look for "color": key
        color_pattern = r'"color":\s*practice_color'
        color_match = re.search(color_pattern, content)

        if not color_match:
            # Try alternative patterns
            color_pattern2 = r'"color":\s*[A-Z_a-z]'
            color_match = re.search(color_pattern2, content)

        if color_match:
            line_end = content.find("\n", color_match.end())
            why_block = '''
            "practice_why": PLANET_WHY.get(planet, {}).get("why", ""),
            "practice_why_science": PLANET_WHY.get(planet, {}).get("why_science", ""),
            "duration_days": PLANET_WHY.get(planet, {}).get("duration_days", 21),
            "duration_label": PLANET_WHY.get(planet, {}).get("duration_label", "21 days"),
            "duration_reason": PLANET_WHY.get(planet, {}).get("duration_reason", ""),
            "best_day": PLANET_WHY.get(planet, {}).get("best_day", ""),
            "best_time": PLANET_WHY.get(planet, {}).get("best_time", ""),
            "completion_milestone": PLANET_WHY.get(planet, {}).get("completion_milestone", ""),'''
            content = content[:line_end] + why_block + content[line_end:]
            print("✓ Added practice_why + duration fields to primary_practice dict")
            changes_made += 1
        else:
            print("⚠ Could not find primary_practice dict assembly point")
            print("  Manually add PLANET_WHY.get(planet, {}).get('why', '') fields")
    else:
        print("⊘ practice_why fields already exist")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 5: Add JSONB key fallbacks for sleeping_planets and rin_debts
    # ═══════════════════════════════════════════════════════════════

    if 'lk.get("advanced")' not in content and "lk.get('advanced')" not in content:
        # Find where sleeping_planets is extracted
        sleeping_patterns = [
            'lk.get("sleeping_planets"',
            "lk.get('sleeping_planets'",
            'lk_data.get("sleeping_planets"',
        ]
        for sp in sleeping_patterns:
            idx = content.find(sp)
            if idx > 0:
                line_start = content.rfind("\n", 0, idx) + 1
                line_end = content.find("\n", idx)
                old_line = content[line_start:line_end]
                # Replace with a fallback that checks 'advanced' key too
                indent = len(old_line) - len(old_line.lstrip())
                spaces = " " * indent
                new_line = old_line.replace(
                    sp,
                    sp.replace(
                        'lk.get("sleeping_planets"',
                        '(lk.get("advanced") or lk).get("sleeping_planets"'
                    ).replace(
                        "lk.get('sleeping_planets'",
                        "(lk.get('advanced') or lk).get('sleeping_planets'"
                    ).replace(
                        'lk_data.get("sleeping_planets"',
                        '(lk_data.get("advanced") or lk_data).get("sleeping_planets"'
                    )
                )
                if new_line != old_line:
                    content = content[:line_start] + new_line + content[line_end:]
                    print("✓ Added 'advanced' key fallback for sleeping_planets")
                    changes_made += 1
                    break

        # Same for rin_debts
        rin_patterns = [
            'lk.get("rin_debts"',
            "lk.get('rin_debts'",
            'lk_data.get("rin_debts"',
        ]
        for rp in rin_patterns:
            idx = content.find(rp)
            if idx > 0:
                line_start = content.rfind("\n", 0, idx) + 1
                line_end = content.find("\n", idx)
                old_line = content[line_start:line_end]
                new_line = old_line.replace(rp, rp.replace(
                    'lk.get("rin_debts"', '(lk.get("advanced") or lk).get("rin_debts"'
                ).replace(
                    "lk.get('rin_debts'", "(lk.get('advanced') or lk).get('rin_debts'"
                ).replace(
                    'lk_data.get("rin_debts"', '(lk_data.get("advanced") or lk_data).get("rin_debts"'
                ))
                if new_line != old_line:
                    content = content[:line_start] + new_line + content[line_end:]
                    print("✓ Added 'advanced' key fallback for rin_debts")
                    changes_made += 1
                    break
    else:
        print("⊘ JSONB advanced key fallbacks already exist")

    # ═══════════════════════════════════════════════════════════════
    # WRITE
    # ═══════════════════════════════════════════════════════════════

    if changes_made == 0:
        print("\n⚠ No changes applied automatically.")
        print("  The file structure may differ from expected.")
        print_manual_instructions()
        return False

    with open(TARGET, "w") as f:
        f.write(content)

    print(f"\n✓ {changes_made} change(s) applied to {TARGET}")
    print(f"  Backup: {BACKUP}")
    print(f"\n  SYNTAX CHECK:")
    print(f"  python3 -c \"import ast; ast.parse(open('{TARGET}').read()); print('Syntax OK')\"")
    print(f"\n  DEPLOY:")
    print(f"  git add -A && git commit -m 'feat: practice WHY + duration + frequency_hz (S6)' && git push")
    print(f"\n  VERIFY:")
    print(f"  curl '.../practices/de02bb52.../schedule?refresh=true' | python3 -m json.tool | grep -E 'frequency_hz|practice_why|duration_label'")
    return True


def print_manual_instructions():
    print("""
═══════════════════════════════════════════════════════════════
MANUAL EDITS (if auto-patch failed)
═══════════════════════════════════════════════════════════════

1. Add PLANET_FREQUENCIES dict near the top of practice_engine.py:
   PLANET_FREQUENCIES = {
     "Sun": 126.22, "Moon": 210.42, "Mars": 144.72, "Mercury": 141.27,
     "Jupiter": 183.58, "Venus": 221.23, "Saturn": 147.85,
     "Rahu": 170.00, "Ketu": 136.10,
   }

2. In the primary_practice dict, add:
   "frequency_hz": PLANET_FREQUENCIES.get(planet, 136.10),
   "practice_why": PLANET_WHY.get(planet, {}).get("why", ""),
   "duration_label": PLANET_WHY.get(planet, {}).get("duration_label", "21 days"),
   "best_day": PLANET_WHY.get(planet, {}).get("best_day", ""),
   "best_time": PLANET_WHY.get(planet, {}).get("best_time", ""),
   "completion_milestone": PLANET_WHY.get(planet, {}).get("completion_milestone", ""),

3. In the mantra_of_the_day dict, add:
   "frequency_hz": PLANET_FREQUENCIES.get(planet, 136.10),

4. For sleeping_planets extraction, add 'advanced' key fallback:
   Change: lk.get("sleeping_planets", [])
   To:     (lk.get("advanced") or lk).get("sleeping_planets", [])

   Change: lk.get("rin_debts", [])
   To:     (lk.get("advanced") or lk).get("rin_debts", [])
═══════════════════════════════════════════════════════════════
""")


if __name__ == "__main__":
    success = patch()
    if success:
        try:
            import ast
            with open(TARGET) as f:
                ast.parse(f.read())
            print("✓ Syntax OK")
        except SyntaxError as e:
            print(f"✗ SYNTAX ERROR: {e}")
            print(f"  Restore: cp {BACKUP} {TARGET}")
