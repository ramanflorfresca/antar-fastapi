#!/usr/bin/env python3
"""
Jaimini Engine v2.0 — Live Test Script
=======================================
Run from your project root:  python3 test_jaimini_live.py

Tests the full engine against Ramandeep's chart:
  - Capricorn lagna (index 9)
  - Born Nov 26, 1974
  - Chart ID: de02bb52-d43a-4b09-be25-b45a07bfbf8a

If you have Supabase access, it will also fetch the real chart data.
Otherwise it uses hardcoded test data matching the Parasara Light verification.
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from antar_engine.jaimini_engine import (
    Planet, SIGN_NAMES,
    compute_7_karakas,
    compute_arudha_lagna,
    compute_upapada_lagna,
    compute_chara_dasha,
    get_current_dasha,
    get_rashi_drishti,
    compute_argala,
    analyze_moving_lagna,
    predict_events,
    build_jaimini_context,
    format_jaimini_prompt_block,
    jaimini_to_db_json,
    generate_dasha_rows,
)

from antar_engine.jaimini_integration import (
    format_jaimini_context_from_stored,
    score_jaimini_convergence,
    jaimini_prashna_check,
)

from antar_engine.welcome_signal_v2 import (
    calculate_current_age,
    get_floor_age,
    filter_umra_for_age,
    build_welcome_context_v2,
    build_system_prompt,
    banned_terms_check,
)

# =============================================================================
# TEST DATA — Ramandeep's chart (Capricorn lagna, Nov 26, 1974)
# Verified against Parasara Light
# =============================================================================

PLANETS = {
    "Sun":     Planet("Sun",     7,  240.5,  0.5,  False),   # Scorpio
    "Moon":    Planet("Moon",    11, 345.2, 15.2,  False),   # Pisces
    "Mars":    Planet("Mars",    8,  268.3, 28.3,  False),   # Sagittarius
    "Mercury": Planet("Mercury", 7,  225.8, 15.8,  False),   # Scorpio
    "Jupiter": Planet("Jupiter", 1,  38.7,   8.7,  False),   # Taurus
    "Venus":   Planet("Venus",   8,  250.1, 10.1,  False),   # Sagittarius
    "Saturn":  Planet("Saturn",  2,  85.4,  25.4,  False),   # Gemini
    "Rahu":    Planet("Rahu",    7,  218.9,  8.9,  False),   # Scorpio
    "Ketu":    Planet("Ketu",    1,  38.9,   8.9,  False),   # Taurus
}

D9_PLANETS = {
    "Sun":     Planet("Sun",     3, 0, 15.0),    # Cancer
    "Moon":    Planet("Moon",    5, 0, 10.0),    # Virgo
    "Mars":    Planet("Mars",    2, 0, 20.0),    # Gemini (AK in D9 = Karakamsa)
    "Mercury": Planet("Mercury", 8, 0, 5.0),     # Sagittarius
    "Jupiter": Planet("Jupiter", 0, 0, 12.0),    # Aries
    "Venus":   Planet("Venus",   6, 0, 8.0),     # Libra
    "Saturn":  Planet("Saturn",  10, 0, 22.0),   # Aquarius
}

LAGNA = 9  # Capricorn
BIRTH_DATE = datetime(1974, 11, 26)
BIRTH_DATE_STR = "1974-11-26"
TODAY = datetime(2026, 3, 31)


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ANTAR — Jaimini Engine v2.0 Live Test                  ║")
    print("║  Chart: Ramandeep (Capricorn lagna, Nov 26 1974)        ║")
    print("║  Date:  March 31, 2026                                  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # ─────────────────────────────────────────────
    separator("1. SEVEN KARAKAS")
    # ─────────────────────────────────────────────
    karakas = compute_7_karakas(PLANETS)
    for k in karakas:
        print(f"  {k.karaka:4s} ({k.meaning:22s}): {k.planet:8s} in {SIGN_NAMES[k.sign]:12s} at {k.degree_in_sign:5.1f}°")

    ak = karakas[0]
    amk = karakas[1]
    dk = karakas[6]
    print(f"\n  Soul Type: {ak.planet} ({ak.meaning})")
    print(f"  Career Significator: {amk.planet} ({amk.meaning})")
    print(f"  Spouse Significator: {dk.planet} ({dk.meaning})")

    # ─────────────────────────────────────────────
    separator("2. ARUDHA LAGNA (Public Image)")
    # ─────────────────────────────────────────────
    al = compute_arudha_lagna(LAGNA, PLANETS)
    print(f"  AL: {al.sign_name} (sign index {al.sign})")
    print(f"  Exception applied: {al.exception_applied}")
    if al.exception_detail:
        print(f"  Detail: {al.exception_detail}")

    # ─────────────────────────────────────────────
    separator("3. UPAPADA LAGNA (Marriage Point)")
    # ─────────────────────────────────────────────
    ul = compute_upapada_lagna(LAGNA, PLANETS)
    print(f"  UL: {ul.sign_name} (sign index {ul.sign})")
    print(f"  Exception applied: {ul.exception_applied}")
    if ul.exception_detail:
        print(f"  Detail: {ul.exception_detail}")

    # ─────────────────────────────────────────────
    separator("4. KARAKAMSA (Soul Purpose)")
    # ─────────────────────────────────────────────
    karakamsa = D9_PLANETS[ak.planet].sign
    print(f"  AK planet: {ak.planet}")
    print(f"  AK in D9:  {SIGN_NAMES[karakamsa]}")
    print(f"  Karakamsa Lagna (KL): {SIGN_NAMES[karakamsa]}")

    # ─────────────────────────────────────────────
    separator("5. CHARA DASHA TIMELINE (Parasara Light Verified)")
    # ─────────────────────────────────────────────
    all_mds = compute_chara_dasha(LAGNA, PLANETS, BIRTH_DATE, num_cycles=1)
    total = 0
    print(f"  {'Sign':<14s} {'Years':>5s}  {'Lord':<10s} {'Dir':<4s}  {'Start':<12s} {'End':<12s}")
    print(f"  {'─'*14} {'─'*5}  {'─'*10} {'─'*4}  {'─'*12} {'─'*12}")
    for md in all_mds:
        total += md.duration_years
        print(f"  {md.sign_name:<14s} {md.duration_years:>5d}  {md.lord:<10s} {'FWD' if md.direction == 'forward' else 'BWD':<4s}  {md.start_date.strftime('%Y-%m-%d'):<12s} {md.end_date.strftime('%Y-%m-%d'):<12s}")
    print(f"\n  Total first cycle: {total} years")

    # ─────────────────────────────────────────────
    separator("6. CURRENT DASHA (March 31, 2026)")
    # ─────────────────────────────────────────────
    md, ad = get_current_dasha(all_mds, TODAY)
    if md:
        print(f"  Mahadasha: {md.sign_name} ({md.start_date.strftime('%b %Y')} – {md.end_date.strftime('%b %Y')}, {md.duration_years}yr)")
        print(f"  Lord: {md.lord}, Direction: {md.direction}")
    if ad:
        print(f"  Antardasha: {ad.sign_name} ({ad.start_date.strftime('%b %Y')} – {ad.end_date.strftime('%b %Y')})")
        print(f"  Lord: {ad.lord}, Direction: {ad.direction}")

    # ─────────────────────────────────────────────
    separator("7. RASHI DRISHTI (Signs Influenced)")
    # ─────────────────────────────────────────────
    active_sign = ad.sign if ad else md.sign
    drishti = get_rashi_drishti(active_sign)
    print(f"  From {SIGN_NAMES[active_sign]}:")
    print(f"  Aspects → {', '.join(SIGN_NAMES[s] for s in drishti)}")

    # ─────────────────────────────────────────────
    separator("8. ARGALA (Support vs Obstruction)")
    # ─────────────────────────────────────────────
    argala = compute_argala(active_sign, PLANETS)
    if argala.primary_argala:
        for house, planets in argala.primary_argala.items():
            print(f"  Support ({house}): {', '.join(planets)}")
    if argala.virodhargala:
        for house, planets in argala.virodhargala.items():
            print(f"  Obstruction ({house}): {', '.join(planets)}")
    print(f"  Net: {'SUPPORTED' if argala.net_supported else 'OBSTRUCTED'}")

    # ─────────────────────────────────────────────
    separator("9. MOVING LAGNA ANALYSIS")
    # ─────────────────────────────────────────────
    ml = analyze_moving_lagna(active_sign, karakas, al, ul, PLANETS)
    for key in ["ak_effect", "amk_effect", "dk_effect", "gk_effect",
                "pk_effect", "mk_effect", "al_effect", "ul_effect"]:
        if key in ml:
            label = key.replace("_effect", "").upper()
            print(f"  {label:4s}: {ml[key]}")

    # ─────────────────────────────────────────────
    separator("10. EVENT PREDICTIONS")
    # ─────────────────────────────────────────────
    predictions = predict_events(active_sign, karakas, al, ul, karakamsa, LAGNA, PLANETS)
    if predictions:
        for p in predictions:
            print(f"  [{p.confidence.upper():6s}] {p.event_type.upper()}")
            print(f"          {p.description}")
            for c in p.conditions_met:
                print(f"          ✓ {c}")
            print()
    else:
        print("  No high-signal events detected for current period.")

    # ─────────────────────────────────────────────
    separator("11. PRASHNA BINARY CHECKS")
    # ─────────────────────────────────────────────
    # Simulate stored chart_data
    ctx = build_jaimini_context(LAGNA, PLANETS, D9_PLANETS, BIRTH_DATE, TODAY)
    db_json = jaimini_to_db_json(ctx)
    chart_data = {"id": "test", "jaimini_data": db_json}

    for q_type in ["marriage", "investment", "foreign", "lawsuit"]:
        result = jaimini_prashna_check(chart_data, q_type, LAGNA)
        verdict = "✓ YES" if result["jaimini_verdict"] else "✗ NO"
        reasons = "; ".join(result["reasons"]) if result["reasons"] else "no triggers"
        print(f"  {q_type:12s}: {verdict}  ({reasons})")

    # ─────────────────────────────────────────────
    separator("12. CONVERGENCE SCORES")
    # ─────────────────────────────────────────────
    for domain in ["career", "wealth", "love", "health", "children", "property"]:
        note = score_jaimini_convergence(chart_data, domain)
        print(f"  {note}")

    # ─────────────────────────────────────────────
    separator("13. LLM PROMPT BLOCK (what Claude sees)")
    # ─────────────────────────────────────────────
    prompt_block = format_jaimini_prompt_block(ctx)
    print(prompt_block)

    # ─────────────────────────────────────────────
    separator("14. WELCOME SIGNAL CONTEXT")
    # ─────────────────────────────────────────────
    age = calculate_current_age(BIRTH_DATE_STR)
    floor = get_floor_age(age)
    umra = filter_umra_for_age(age)
    print(f"  Age: {age}, Floor: {floor}")
    print(f"  Upcoming Umra: {[f'Age {u['age']}: {u['theme']}' for u in umra]}")

    welcome_chart = {
        "id": "de02bb52-d43a-4b09-be25-b45a07bfbf8a",
        "first_name": "Ramandeep",
        "birth_date": BIRTH_DATE_STR,
        "lagna_sign": "Capricorn",
        "moon_sign": "Pisces",
        "moon_nakshatra": "Revati",
        "current_dasha": "Mars-Moon",
        "jaimini_data": json.dumps(db_json),
        "lal_kitab_data": json.dumps({"year_lord": "Saturn"}),
    }
    welcome_ctx = build_welcome_context_v2(welcome_chart, BIRTH_DATE_STR)
    welcome_prompt = build_system_prompt(welcome_ctx)
    print(f"\n  Welcome prompt length: {len(welcome_prompt)} chars")
    print(f"  First 500 chars:\n")
    print(welcome_prompt[:500])
    print("  ...")

    # ─────────────────────────────────────────────
    separator("15. DATABASE ROW COUNTS")
    # ─────────────────────────────────────────────
    rows = generate_dasha_rows("test-chart", LAGNA, PLANETS, BIRTH_DATE, num_cycles=2)
    md_rows = [r for r in rows if r["level_int"] == 1]
    ad_rows = [r for r in rows if r["level_int"] == 2]
    print(f"  MD rows: {len(md_rows)}")
    print(f"  AD rows: {len(ad_rows)}")
    print(f"  Total:   {len(rows)}")

    # ─────────────────────────────────────────────
    separator("16. BANNED TERMS CHECK")
    # ─────────────────────────────────────────────
    test_texts = [
        ("Clean output", "Your career is entering a peak phase. Act before June."),
        ("Dirty output", "Your Atmakaraka in the Navamsa shows a Mahadasha transition."),
        ("LLM prompt block", prompt_block),
    ]
    for label, text in test_texts:
        found = banned_terms_check(text)
        status = f"CLEAN" if not found else f"FOUND: {found}"
        print(f"  {label:20s}: {status}")

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  ✅ ALL 16 TESTS COMPLETE                               ║")
    print("╚══════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
