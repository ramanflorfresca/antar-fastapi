"""
patch_age_adaptive_proof.py
Run: python patch_age_adaptive_proof.py

Upgrades the welcome signal with:
1. Age-adaptive proof strategy (18-24 / 25-40 / 40+)
2. Migration detection when birth_country != current_country
3. Signal 3 connected to the arc ("chapter 4 of your story")
4. Min age floor based on user's current age (not fixed at 16)
5. current_country passed through to convergence engine
"""

filepath = "antar_engine/welcome_signal.py"

with open(filepath, "r") as f:
    content = f.read()

patches_applied = 0

# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 1: Update _build_convergence_proof signature to accept current_age + country
# ═══════════════════════════════════════════════════════════════════════════════

old_proof_sig = '''def _build_convergence_proof(
    chart_id: str,
    chart_data: dict,
    birth_date: str,
    supabase,
) -> str:'''

new_proof_sig = '''def _build_convergence_proof(
    chart_id: str,
    chart_data: dict,
    birth_date: str,
    supabase,
    current_age: int = None,
    birth_country: str = "",
    current_country: str = "",
) -> str:'''

if old_proof_sig in content:
    content = content.replace(old_proof_sig, new_proof_sig)
    patches_applied += 1
    print("✅ Patch 1: Convergence proof signature updated with age + country params")
else:
    print("⚠️  Patch 1 SKIPPED: could not find convergence proof signature")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 2: Replace age floor logic — age-adaptive instead of fixed 16
# ═══════════════════════════════════════════════════════════════════════════════

old_age_filter = """                # Skip childhood (before age 16)
                if age_end < 16:
                    continue"""

new_age_filter = """                # Age-adaptive floor:
                # 40+ users: skip events before age 25 (focus on peak life)
                # 25-40 users: skip events before age 18 (include career/migration)
                # 18-24 users: skip events before age 16
                if current_age and current_age >= 40:
                    _min_event_age = 25
                elif current_age and current_age >= 25:
                    _min_event_age = 18
                else:
                    _min_event_age = 16
                if age_end < _min_event_age:
                    continue"""

if old_age_filter in content:
    content = content.replace(old_age_filter, new_age_filter)
    patches_applied += 1
    print("✅ Patch 2: Age-adaptive floor applied (40+→25, 25-40→18, 18-24→16)")
else:
    print("⚠️  Patch 2 SKIPPED: could not find age filter block")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 3: Add migration detection after convergence loop
# Insert after "if not convergences:" check, before the sort
# ═══════════════════════════════════════════════════════════════════════════════

old_no_convergences = """    if not convergences:
        return ""

    # ── Sort by recency and significance, take top 3 ─────────────
    # Prefer: recent, longer overlap, transformation houses (7,8,10)
    priority_houses = {8: 3, 7: 2, 10: 2, 6: 1, 1: 1}"""

new_with_migration = """    # ── Migration detection ─────────────────────────────────────
    # If birth_country != current_country, find the 12th/9th/Rahu period
    # that most likely corresponds to when they left home
    _is_migrant = (
        birth_country and current_country
        and birth_country.strip().upper() != current_country.strip().upper()
    )
    if _is_migrant:
        # Look for 12th house, 9th house, or Rahu-linked periods in age 16-30
        migration_houses = {12, 9}
        migration_candidates = []
        for c in convergences:
            if c["house"] in migration_houses and c["age_start"] >= 16 and c["age_start"] <= 35:
                migration_candidates.append(c)
        
        # Also check for Rahu periods (even without house convergence)
        for vim in vim_periods:
            vim_planet = vim["planet_or_sign"]
            if vim_planet == "Rahu":
                vim_start = date.fromisoformat(str(vim["start_date"])[:10])
                vim_end = date.fromisoformat(str(vim["end_date"])[:10])
                rahu_age_start = vim_start.year - bd.year
                rahu_age_end = vim_end.year - bd.year
                if rahu_age_start <= 35 and rahu_age_end >= 16 and vim_end <= today:
                    # Check if already in convergences
                    already_found = any(
                        c["vim_planet"] == "Rahu" and abs(c["start_year"] - vim_start.year) < 3
                        for c in convergences
                    )
                    if not already_found:
                        _mig_start = max(vim_start.year, bd.year + 16)
                        _mig_end = min(vim_end.year, today.year)
                        _mig_age_s = max(rahu_age_start, 16)
                        _mig_age_e = min(rahu_age_end, today.year - bd.year)
                        migration_candidates.append({
                            "house": 12,
                            "vim_planet": "Rahu",
                            "jai_sign": "migration",
                            "start_year": _mig_start,
                            "end_year": _mig_end,
                            "age_start": _mig_age_s,
                            "age_end": _mig_age_e,
                            "overlap_years": (_mig_end - _mig_start),
                            "theme": "migration",
                            "chapter": "The crossing",
                            "question": f"Around {_mig_start}–{_mig_end}, did you leave your home country — a move that felt like starting from zero in a completely new world?",
                            "meaning": "This was not exile. It was the chart redirecting your entire trajectory — everything you have built since was only possible because you left.",
                        })
        
        if migration_candidates:
            # Add best migration candidate if not already in convergences
            migration_candidates.sort(key=lambda c: c["start_year"])
            best_mig = migration_candidates[0]
            already_has = any(
                c["house"] == best_mig["house"]
                and abs(c["start_year"] - best_mig["start_year"]) < 3
                for c in convergences
            )
            if not already_has:
                convergences.append(best_mig)

    if not convergences:
        return ""

    # ── Sort by recency and significance, take top 3 ─────────────
    # Prefer: recent, longer overlap, transformation houses (7,8,10,12 for migration)
    priority_houses = {8: 3, 7: 2, 10: 2, 12: 2, 6: 1, 1: 1}"""

if old_no_convergences in content:
    content = content.replace(old_no_convergences, new_with_migration)
    patches_applied += 1
    print("✅ Patch 3: Migration detection added (birth_country != current_country)")
else:
    print("⚠️  Patch 3 SKIPPED: could not find convergence sort block")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 4: Update convergence caller to pass current_age + country
# ═══════════════════════════════════════════════════════════════════════════════

old_proof_call = """    if chart_id and supabase and birth_date and current_age and current_age > 25:
        try:
            proof_block = _build_convergence_proof(chart_id, chart_data, birth_date, supabase)"""

new_proof_call = """    if chart_id and supabase and birth_date and current_age and current_age >= 18:
        try:
            proof_block = _build_convergence_proof(
                chart_id, chart_data, birth_date, supabase,
                current_age=current_age,
                birth_country=country_code or "",
                current_country=_current_country or country_code or "",
            )"""

if old_proof_call in content:
    content = content.replace(old_proof_call, new_proof_call)
    patches_applied += 1
    print("✅ Patch 4: Convergence caller updated — age >= 18, passes country")
else:
    # Try without the _current_country variable (might not exist in context builder)
    old_proof_call2 = """    if chart_id and supabase and birth_date and current_age and current_age > 25:
        try:
            proof_block = _build_convergence_proof(chart_id, chart_data, birth_date, supabase)"""
    if old_proof_call2 in content:
        content = content.replace(old_proof_call2, """    if chart_id and supabase and birth_date and current_age and current_age >= 18:
        try:
            proof_block = _build_convergence_proof(
                chart_id, chart_data, birth_date, supabase,
                current_age=current_age,
                birth_country=country_code or "",
                current_country=country_code or "",
            )""")
        patches_applied += 1
        print("✅ Patch 4: Convergence caller updated (alt — uses country_code for both)")
    else:
        print("⚠️  Patch 4 SKIPPED: could not find proof call block")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 5: Add young user strategy to context block
# When age < 25 and no proof events, switch to "what you're feeling now" strategy
# ═══════════════════════════════════════════════════════════════════════════════

old_context_end = """    lines.append("FINAL THREAD (after the 3 proof events):")
    lines.append("Connect all three events to the present. The user should feel that")
    lines.append("every chapter — the break, the reckoning, the fight — led directly")
    lines.append("to what they are doing right now. The present is not accidental.")
    lines.append("")"""

new_context_end = """    # Add age-specific strategy note
    if current_age and current_age < 25:
        lines.append("AGE NOTE: This user is under 25. If proof events are thin or absent,")
        lines.append("Signal 2 should INSTEAD name what they are struggling with RIGHT NOW")
        lines.append("with uncomfortable specificity — the tension between family expectations")
        lines.append("and personal desire, the career decision they are avoiding, the relationship")
        lines.append("question they already know the answer to. Make it feel private and precise.")
        lines.append("Format: still use the proof JSON structure but with 1 event that describes")
        lines.append("the CURRENT tension, not a past event. Thread connects to Signal 3.")
        lines.append("")
    
    lines.append("FINAL THREAD (after the proof events):")
    lines.append("Connect all events to the present. The user should feel that")
    lines.append("every chapter — the break, the reckoning, the fight — led directly")
    lines.append("to what they are doing right now. The present is not accidental.")
    lines.append("")"""

if old_context_end in content:
    content = content.replace(old_context_end, new_context_end)
    patches_applied += 1
    print("✅ Patch 5: Young user strategy added (under 25 = present tension)")
else:
    print("⚠️  Patch 5 SKIPPED: could not find context end block")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 6: Update Signal 3 system prompt — connect to the arc
# ═══════════════════════════════════════════════════════════════════════════════

old_signal3_prompt = """SIGNAL 3 — THE SIGNAL
One specific thing to watch for in the next 60-90 days.
Based on current planetary period + slow planet transits.
Name the domain. Name the date range. End with one action or thing to watch for.
2-3 sentences."""

new_signal3_prompt = """SIGNAL 3 — THE PAYOFF
This is chapter 4 of the story you just told in Signal 2.
The proof events showed what happened. Signal 3 shows what it was all leading to.

One specific thing to watch for in the next 60-90 days.
Based on current planetary period + slow planet transits.
Name the domain. Name the date range. End with one action or thing to watch for.

CRITICAL: Connect this to the thread from Signal 2. Reference the arc.
NOT: "A financial door opens in April."
YES: "Everything those chapters cost you starts paying back now. Between April and June, a financial door opens through your network — act on it within the week."

2-3 sentences. The user should feel this is the destination, not random advice."""

if old_signal3_prompt in content:
    content = content.replace(old_signal3_prompt, new_signal3_prompt)
    patches_applied += 1
    print("✅ Patch 6: Signal 3 prompt updated — connects to arc as 'chapter 4'")
else:
    print("⚠️  Patch 6 SKIPPED: could not find Signal 3 prompt")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 7: Add migration house question templates  
# Add to HOUSE_QUESTIONS dict and CHAPTER_NAMES
# ═══════════════════════════════════════════════════════════════════════════════

# Add "The crossing" as an alternate chapter name for house 12 when migration detected
# This is handled in the migration detection code (Patch 3) directly
# No separate patch needed — the migration_candidates already use custom question/meaning

# But let's add house 12 migration variant to the priority list
old_priority = """    priority_houses = {8: 3, 7: 2, 10: 2, 12: 2, 6: 1, 1: 1}"""
# Already updated in Patch 3, so skip
if old_priority in content:
    print("✅ Patch 7: Migration house (12) already in priority list from Patch 3")
    patches_applied += 1
else:
    # Check if old priority without 12 exists
    old_priority_orig = """    priority_houses = {8: 3, 7: 2, 10: 2, 6: 1, 1: 1}"""
    if old_priority_orig in content:
        content = content.replace(old_priority_orig, old_priority)
        patches_applied += 1
        print("✅ Patch 7: Added house 12 to priority list")
    else:
        print("⚠️  Patch 7 SKIPPED: priority houses already updated or not found")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 8: Update rule 5 in system prompt — Signal 2 dates are PAST not future
# ═══════════════════════════════════════════════════════════════════════════════

old_rule5 = "5. All dates in Signal 2 and Signal 3 must be in the FUTURE. Never reference a date that has passed."
new_rule5 = "5. Signal 2 dates are PAST events (proof). Signal 3 dates must be in the FUTURE. The proof is about what already happened — the signal is about what is coming."

if old_rule5 in content:
    content = content.replace(old_rule5, new_rule5)
    patches_applied += 1
    print("✅ Patch 8: Rule 5 updated — Signal 2 = past, Signal 3 = future")
else:
    print("⚠️  Patch 8 SKIPPED: could not find rule 5")


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 9: Remove rule 6 about Signal 2 timing (no longer needed — proof has periods not timing)
# ═══════════════════════════════════════════════════════════════════════════════

old_rule6 = "6. Signal 2 timing must be a specific Month YYYY at least 1 month in the future.\n"
new_rule6 = "6. Signal 2 proof events must use the exact periods provided in the context — do not invent dates.\n"

if old_rule6 in content:
    content = content.replace(old_rule6, new_rule6)
    patches_applied += 1
    print("✅ Patch 9: Rule 6 updated for proof events")
else:
    print("⚠️  Patch 9 SKIPPED: could not find rule 6")


# ═══════════════════════════════════════════════════════════════════════════════
# WRITE + VERIFY
# ═══════════════════════════════════════════════════════════════════════════════

with open(filepath, "w") as f:
    f.write(content)

# Syntax check
import ast
try:
    ast.parse(content)
    print(f"\n✅ Syntax check PASSED")
except SyntaxError as e:
    print(f"\n❌ Syntax ERROR at line {e.lineno}: {e.msg}")
    print(f"   Fix this before deploying!")

print(f"\n{'='*60}")
print(f"Applied {patches_applied} patches to {filepath}")
print(f"{'='*60}")

if patches_applied >= 7:
    print("\n✅ Patch looks good. Next steps:")
    print("  1. git add antar_engine/welcome_signal.py")
    print("  2. git commit -m 'feat: age-adaptive proof, migration detection, Signal 3 arc connection'")
    print("  3. git push")
    print("  4. DELETE FROM welcome_signals WHERE chart_id = 'de02bb52-d43a-4b09-be25-b45a07bfbf8a';")
    print("  5. curl the welcome endpoint and verify")
else:
    print(f"\n⚠️  Only {patches_applied} patches applied. Review warnings above.")
