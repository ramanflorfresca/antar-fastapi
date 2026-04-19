#!/usr/bin/env python3
"""
test_v5_actionability.py
=========================
Tests for v5 Actionability Layer + v5.1 Voice Framework.

Tests validate:
  1. Lal Kitab remedy database (all planets, lookup)
  2. Context-aware remedy selection (contraindications, category filtering)
  3. Actionability enrichment (WHY/DO/DON'T for each finding)
  4. Energy vocabulary (planet→energy translation)
  5. Voice templates (A/B/C selection)
  6. Forbidden terms linter (jargon detection)
  7. Integration: enrichment on real chart data
  8. Regression: v2/v3/v4 output still intact

Usage:
    cd ~/antarai && source venv311/bin/activate
    python test_v5_actionability.py
"""

import sys

sys.path.insert(0, ".")

from antar_engine.life_arc.remedies.lal_kitab_database import (
    ALL_REMEDIES, REMEDY_BY_ID, get_remedies_for_planet, get_remedy_by_id,
    LalKitabRemedy,
)
from antar_engine.life_arc.remedies.remedy_selector import (
    select_appropriate_remedy, select_deactivation_remedy,
)
from antar_engine.life_arc.actionability import (
    enrich_signature_with_actionability, actionability_summary,
    ActionabilityBlock,
)
from antar_engine.life_arc.voice.energy_vocabulary import (
    PLANET_ENERGY_VOCABULARY, get_energy_name, get_felt_sense, get_chakra,
)
from antar_engine.life_arc.voice.templates import (
    select_template, render_template, get_template_text,
)
from antar_engine.life_arc.voice.voice_prompter import (
    build_voice_prompt, build_batch_voice_prompts,
)
from antar_engine.life_arc.voice.forbidden_terms import (
    check_forbidden_terms, is_voice_clean, FORBIDDEN_TERMS,
)
from antar_engine.life_arc.signatures.business_fit import analyze_business_fit


# ─── MOCK CHART DATA ───────────────────────────────────────────────────────

# Raman: Capricorn rising, Saturn yogakaraka in H6, focus-split risk
RAMAN_CHART = {
    "lagna": {"sign_index": 9, "sign": "Capricorn"},
    "planets": {
        "Sun": {"sign_index": 7, "sign": "Scorpio", "house": 11, "degree": 15.0, "longitude": 225.0, "nakshatra": "Anuradha", "nakshatra_lord": "Saturn"},
        "Moon": {"sign_index": 11, "sign": "Pisces", "house": 3, "degree": 28.0, "longitude": 358.0, "nakshatra": "Revati", "nakshatra_lord": "Mercury"},
        "Mars": {"sign_index": 6, "sign": "Libra", "house": 10, "degree": 20.0, "longitude": 200.0, "nakshatra": "Swati", "nakshatra_lord": "Rahu"},
        "Mercury": {"sign_index": 6, "sign": "Libra", "house": 10, "degree": 5.0, "longitude": 185.0, "nakshatra": "Chitra", "nakshatra_lord": "Mars"},
        "Jupiter": {"sign_index": 10, "sign": "Aquarius", "house": 2, "degree": 12.0, "longitude": 312.0, "nakshatra": "Shatabhisha", "nakshatra_lord": "Rahu"},
        "Venus": {"sign_index": 7, "sign": "Scorpio", "house": 11, "degree": 10.0, "longitude": 220.0, "nakshatra": "Anuradha", "nakshatra_lord": "Saturn"},
        "Saturn": {"sign_index": 2, "sign": "Gemini", "house": 6, "degree": 18.0, "longitude": 78.0, "nakshatra": "Ardra", "nakshatra_lord": "Rahu"},
        "Rahu": {"sign_index": 7, "sign": "Scorpio", "house": 11, "degree": 22.0, "longitude": 232.0, "nakshatra": "Jyeshtha", "nakshatra_lord": "Mercury"},
        "Ketu": {"sign_index": 1, "sign": "Taurus", "house": 5, "degree": 22.0, "longitude": 52.0, "nakshatra": "Rohini", "nakshatra_lord": "Moon"},
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {"lagna": "Cancer", "lagna_lord": "Moon", "sun_hora_planets": ["Mars", "Saturn"], "moon_hora_planets": ["Sun", "Moon", "Mercury", "Jupiter", "Venus", "Rahu"], "wealth_signals": []},
        "d4": {"planets": {"Jupiter": {"sign_index": 3, "house": 7}, "Venus": {"sign_index": 0, "house": 4}, "Mars": {"sign_index": 9, "house": 1}, "Saturn": {"sign_index": 6, "house": 10}}},
        "d7": {"lagna": "Aries", "planets": {}},
        "d9": {"lagna": "Cancer", "planets": {}},
        "d10": {"lagna": "Scorpio", "planets": {"Mercury": {"sign_index": 6, "sign": "Libra", "house": 10}, "Jupiter": {"sign_index": 10, "sign": "Aquarius", "house": 4}, "Venus": {"sign_index": 7, "sign": "Scorpio", "house": 1}, "Mars": {"sign_index": 0, "sign": "Aries", "house": 6}, "Saturn": {"sign_index": 2, "sign": "Gemini", "house": 8}}},
        "d60": {"planet_analysis": {"Mercury": {"karma_name": "Bhrashta", "karma_desc": "fallen karma", "is_positive": False, "is_challenging": True}}},
    },
    "current_dasha": {"md_lord": "Mars", "ad_lord": "Rahu"},
    "archetype": {"name": "The Broker"},
}


# ═══════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════

passed = 0
failed = 0
total = 0


def run_test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")


# ─── GROUP 1: REMEDY DATABASE ──────────────────────────────────────────────
print("\n═══ GROUP 1: Lal Kitab Remedy Database ═══")

# Test 1: All 9 planets have remedies
run_test(
    "All 9 planets have remedies",
    len(ALL_REMEDIES) == 9 and all(len(v) >= 1 for v in ALL_REMEDIES.values()),
    f"Planets: {len(ALL_REMEDIES)}, min remedies: {min(len(v) for v in ALL_REMEDIES.values())}",
)

# Test 2: Total remedies >= 14 (from spec)
total_remedies = sum(len(v) for v in ALL_REMEDIES.values())
run_test(
    "Total remedies >= 14",
    total_remedies >= 14,
    f"Got {total_remedies}",
)

# Test 3: Remedy lookup by ID works
saturn_remedy = get_remedy_by_id("saturn_flour_water_mustard")
run_test(
    "Remedy lookup by ID works",
    saturn_remedy is not None and saturn_remedy.target_planet == "Saturn",
    f"Got {saturn_remedy}",
)

# Test 4: All remedies have required fields
all_have_fields = True
for rid, r in REMEDY_BY_ID.items():
    if not r.action or not r.materials or not r.frequency:
        all_have_fields = False
        break
run_test(
    "All remedies have action, materials, frequency",
    all_have_fields,
)

# Test 5: All remedies have failure_mode
all_have_failure = all(r.failure_mode for r in REMEDY_BY_ID.values())
run_test(
    "All remedies have failure_mode documented",
    all_have_failure,
)


# ─── GROUP 2: REMEDY SELECTOR ─────────────────────────────────────────────
print("\n═══ GROUP 2: Context-Aware Remedy Selection ═══")

# Test 6: Focus-split risk selects Rahu scatter remedy
focus_remedy = select_appropriate_remedy(
    finding_type="focus_split_risk",
    finding_category="NEGATIVE",
    target_planet="Rahu",
    chart_data=RAMAN_CHART,
)
run_test(
    "Focus-split selects Rahu scatter remedy",
    focus_remedy is not None and focus_remedy.remedy_id == "rahu_silver_wire_scatter",
    f"Got {focus_remedy.remedy_id if focus_remedy else 'None'}",
)

# Test 7: Moon MD pressure selects Moon remedy
moon_remedy = select_appropriate_remedy(
    finding_type="moon_md_h2_pressure",
    finding_category="NEGATIVE",
    target_planet="Moon",
    chart_data=RAMAN_CHART,
)
run_test(
    "Moon MD pressure selects Moon remedy",
    moon_remedy is not None and moon_remedy.target_planet == "Moon",
    f"Got {moon_remedy.remedy_id if moon_remedy else 'None'}",
)

# Test 8: Yogakaraka Saturn selects iron-workplace (activation, not suppression)
yk_remedy = select_appropriate_remedy(
    finding_type="yogakaraka_activation",
    finding_category="POSITIVE",
    target_planet="Saturn",
    chart_data=RAMAN_CHART,
)
run_test(
    "Yogakaraka Saturn selects activation remedy (iron workplace)",
    yk_remedy is not None and yk_remedy.remedy_id == "saturn_iron_workplace",
    f"Got {yk_remedy.remedy_id if yk_remedy else 'None'}",
)

# Test 9: Deactivation for focus_split_risk exists
deact = select_deactivation_remedy("focus_split_risk", "Rahu", RAMAN_CHART)
run_test(
    "Deactivation guidance for focus_split exists",
    deact is not None and "action" in deact and "reason" in deact,
    f"Got {deact}",
)

# Test 10: Saturn affliction remedy blocked when Saturn is yogakaraka
# Raman has Saturn as yogakaraka (Capricorn lagna → Venus is yogakaraka, not Saturn)
# Actually for Capricorn, Venus is yogakaraka. So Saturn is NOT yogakaraka here.
# Let's test with a chart where Saturn IS yogakaraka (Taurus lagna)
taurus_chart = {
    "lagna": {"sign_index": 1},
    "planets": {"Saturn": {"sign_index": 6, "house": 6}, "Rahu": {"sign_index": 7, "house": 7}},
    "yogas": [],
    "current_dasha": {},
}
sat_affliction = select_appropriate_remedy(
    finding_type="d60_karma",
    finding_category="NEGATIVE",
    target_planet="Saturn",
    chart_data=taurus_chart,
)
# Should return None because saturn_flour_water_mustard has contraindication "saturn_yogakaraka_active"
# and Taurus lagna has Saturn as yogakaraka
run_test(
    "Saturn affliction remedy blocked when Saturn is yogakaraka",
    sat_affliction is None,
    f"Got {sat_affliction.remedy_id if sat_affliction else 'None'}",
)


# ─── GROUP 3: ACTIONABILITY ENRICHMENT ─────────────────────────────────────
print("\n═══ GROUP 3: Actionability Enrichment ═══")

# Run full analysis on Raman chart
raman_bf = analyze_business_fit(RAMAN_CHART)
blocks = enrich_signature_with_actionability(raman_bf, RAMAN_CHART)

# Test 11: Enrichment produces blocks
run_test(
    "Enrichment produces actionability blocks",
    len(blocks) > 0,
    f"Got {len(blocks)} blocks",
)

# Test 12: All blocks have WHY field
all_have_why = all(b.why_plain_language for b in blocks)
run_test(
    "All blocks have why_plain_language",
    all_have_why,
    f"Empty WHY in: {[b.finding_id for b in blocks if not b.why_plain_language]}",
)

# Test 13: At least one block has a remedy
remedied = [b for b in blocks if b.lal_kitab_activation is not None]
run_test(
    "At least one block has a remedy attached",
    len(remedied) > 0,
    f"Got {len(remedied)} blocks with remedies",
)

# Test 14: Focus-split block exists and is NEGATIVE
focus_blocks = [b for b in blocks if b.finding_id == "focus_split_risk"]
run_test(
    "Focus-split finding exists and is NEGATIVE",
    len(focus_blocks) > 0 and focus_blocks[0].finding_category == "NEGATIVE",
    f"Got {len(focus_blocks)} focus blocks",
)

# Test 15: Yogakaraka block exists and is POSITIVE
yk_blocks = [b for b in blocks if b.finding_id == "yogakaraka_activation"]
run_test(
    "Yogakaraka finding exists and is POSITIVE",
    len(yk_blocks) > 0 and yk_blocks[0].finding_category == "POSITIVE",
    f"Got {len(yk_blocks)} yk blocks",
)

# Test 16: Summary produces valid structure
summary = actionability_summary(blocks)
run_test(
    "Summary has required keys",
    all(k in summary for k in ["total_findings", "positive_findings", "negative_findings", "remedies_available", "blocks"]),
    f"Keys: {list(summary.keys())}",
)


# ─── GROUP 4: ENERGY VOCABULARY ────────────────────────────────────────────
print("\n═══ GROUP 4: Energy Vocabulary (v5.1) ═══")

# Test 17: All 9 planets have energy vocabulary
run_test(
    "All 9 planets have energy vocabulary",
    len(PLANET_ENERGY_VOCABULARY) == 9,
    f"Got {len(PLANET_ENERGY_VOCABULARY)}",
)

# Test 18: Each planet has all required fields
required_fields = ["energy_name", "alt_names", "chakra", "felt_when_strong", "felt_when_weak", "life_domain"]
all_complete = True
missing_info = ""
for planet, vocab in PLANET_ENERGY_VOCABULARY.items():
    for f in required_fields:
        if f not in vocab or not vocab[f]:
            all_complete = False
            missing_info = f"{planet} missing {f}"
            break
run_test(
    "All planets have complete vocabulary",
    all_complete,
    missing_info,
)

# Test 19: No planet names in energy_name fields
no_planet_in_name = all(
    planet.lower() not in vocab["energy_name"].lower()
    for planet, vocab in PLANET_ENERGY_VOCABULARY.items()
)
run_test(
    "No planet names in energy_name fields",
    no_planet_in_name,
)

# Test 20: get_energy_name returns non-empty for Saturn
run_test(
    "get_energy_name('Saturn') returns non-empty",
    get_energy_name("Saturn") == "structure and persistence energy",
    f"Got: {get_energy_name('Saturn')}",
)


# ─── GROUP 5: VOICE TEMPLATES ─────────────────────────────────────────────
print("\n═══ GROUP 5: Voice Templates ═══")

# Test 21: Template selection logic
run_test(
    "POSITIVE yogakaraka → Template A",
    select_template("POSITIVE", "yogakaraka_activation") == "A",
)
run_test(
    "NEGATIVE identity_overwhelm → Template B",
    select_template("NEGATIVE", "identity_overwhelm") == "B",
)
run_test(
    "focus_split_risk → Template C",
    select_template("NEGATIVE", "focus_split_risk") == "C",
)

# Test 24: Template rendering produces non-empty output
rendered = render_template(
    "A",
    energy_name="structure and persistence energy",
    energy_description="the flow that builds reliably over years",
    felt_examples="you stay with hard things longer than most",
    remedy_action="on Saturdays, offer bread with mustard oil",
    expected_observation="operational decisions feel clearer",
    what_not_to_do="don't add a third venture in the next six months",
)
run_test(
    "Template A renders non-empty output",
    len(rendered) > 100 and "structure and persistence" in rendered,
    f"Got {len(rendered)} chars",
)


# ─── GROUP 6: FORBIDDEN TERMS LINTER ──────────────────────────────────────
print("\n═══ GROUP 6: Forbidden Terms Linter ═══")

# Test 25: Clean text passes
run_test(
    "Clean text passes linter",
    is_voice_clean("Your structure energy is one of the strongest flows in your design."),
)

# Test 26: Jargon text fails — planet as subject
violations = check_forbidden_terms("Your Jupiter is weak in the 6th house.")
run_test(
    "Planet-as-subject detected",
    len(violations) > 0,
    f"Got {len(violations)} violations",
)

# Test 27: Jargon text fails — Lal Kitab
run_test(
    "'Lal Kitab' detected as forbidden",
    not is_voice_clean("Lal Kitab prescribes this remedy for Saturn."),
)

# Test 28: Technical terms detected
run_test(
    "Technical term 'dushthana' detected",
    not is_voice_clean("Your planet is in a dushthana house."),
)

# Test 29: Prescriptive language detected
run_test(
    "'You must' detected as forbidden",
    not is_voice_clean("You must do this remedy every day."),
)

# Test 30: Good v5.1 voice output passes linter
good_output = (
    "Your structure and persistence energy — the flow that builds reliably "
    "over years when others burn out — is one of the strongest currents in your design. "
    "You may have noticed you stay with hard things longer than most people. "
    "To let this flow work through you this season, one practice: on Saturdays, "
    "offer a piece of bread with a drop of mustard oil to someone working physically hard. "
    "Over a few weeks, notice whether operational decisions become clearer. "
    "One thing to protect this energy: don't scatter your discipline across multiple new ventures."
)
run_test(
    "Good v5.1 voice output passes linter",
    is_voice_clean(good_output),
    f"Violations: {check_forbidden_terms(good_output)}",
)


# ─── GROUP 7: VOICE PROMPTER ──────────────────────────────────────────────
print("\n═══ GROUP 7: Voice Prompter ═══")

# Test 31: build_voice_prompt produces non-empty prompt
prompt = build_voice_prompt(
    finding_id="yogakaraka_activation",
    finding_category="POSITIVE",
    target_planet="Saturn",
    why_plain_language="Saturn yogakaraka in H6",
    remedy_action="Keep iron in workplace, donate on Saturdays",
    what_not_to_do="Don't scatter across multiple ventures",
    expected_observation="Operational decisions clearer",
)
run_test(
    "build_voice_prompt produces non-empty prompt",
    len(prompt) > 200 and "structure and persistence" in prompt,
    f"Got {len(prompt)} chars",
)

# Test 32: Prompt contains forbidden terms warning
run_test(
    "Prompt contains forbidden terms guidance",
    "NEVER use" in prompt,
)

# Test 33: batch prompts work on actionability blocks
batch = build_batch_voice_prompts(blocks, RAMAN_CHART)
run_test(
    "Batch prompts generated for all blocks",
    len(batch) == len(blocks),
    f"Got {len(batch)} prompts for {len(blocks)} blocks",
)


# ─── GROUP 8: REGRESSION ──────────────────────────────────────────────────
print("\n═══ GROUP 8: Regression Checks ═══")

# Test 34: business_fit still returns all v4 keys
v4_keys = ["wealth_archetype", "viparita_stack", "critical_warnings", "honest_scale_read"]
missing = [k for k in v4_keys if k not in raman_bf]
run_test(
    "business_fit returns v4 keys (regression)",
    len(missing) == 0,
    f"Missing: {missing}",
)

# Test 35: business_fit returns v3 keys
v3_keys = ["modern_corrections", "dushthana_wealth", "lk_negations"]
missing_v3 = [k for k in v3_keys if k not in raman_bf]
run_test(
    "business_fit returns v3 keys (regression)",
    len(missing_v3) == 0,
    f"Missing: {missing_v3}",
)

# Test 36: Signature version is 4.0
run_test(
    "Signature version is 4.0",
    raman_bf.get("signature_version") == "4.0",
    f"Got: {raman_bf.get('signature_version')}",
)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  v5 ACTIONABILITY + v5.1 VOICE TESTS: {passed}/{total} passed, {failed} failed")
print(f"{'═' * 60}")

if failed > 0:
    print("\n⚠️  Some tests failed. Review output above.")
    sys.exit(1)
else:
    print("\n✅ All v5 tests passed!")
    sys.exit(0)
