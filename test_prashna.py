"""
Test Suite for Prashna Engine
==============================
Tests all logic paths without needing Railway or Supabase.
Uses Swiss Ephemeris for real chart casting when available,
falls back to mock data for logic-only tests.

Run: python test_prashna.py
"""

import sys
import json
from datetime import datetime, timezone, timedelta

# Import the engine — works whether prashna_engine.py is in ./  or ./antar_engine/
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "antar_engine"))
sys.path.insert(0, os.path.dirname(__file__))
from prashna_engine import (
    get_rashi_drishti, detect_prashna_intent, detect_domain,
    check_lagna_strength, check_lord_connection, check_ithasala,
    check_ithasala_for_houses, check_moon_validation,
    check_muthashila, check_nakta, check_yamaya, check_edge_yogas,
    check_mutual_reception, compute_prashna_verdict, check_cooldown,
    build_prashna_prompt, find_weakest_planet,
    cast_prashna_chart, run_prashna_engine,
    sign_name, get_sign_lord, planet_name_from_id, get_nakshatra,
    PRASHNA_COOLDOWN_HOURS, SWE_PLANETS,
)

passed = 0
failed = 0
total = 0

def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")

# ═══════════════════════════════════════════════════════════════════
# 1. UTILITY TESTS
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 1. UTILITY TESTS ═══")

test("Sign name Aries", sign_name(0) == "Aries")
test("Sign name Pisces", sign_name(11) == "Pisces")
test("Sign name wraps", sign_name(12) == "Aries")
test("Sign lord Aries=Mars(4)", get_sign_lord(0) == 4)
test("Sign lord Cancer=Moon(1)", get_sign_lord(3) == 1)
test("Sign lord Capricorn=Saturn(6)", get_sign_lord(9) == 6)
test("Planet name Sun", planet_name_from_id(0) == "Sun")
test("Planet name Saturn", planet_name_from_id(6) == "Saturn")

# Nakshatra
nak = get_nakshatra(0.0)
test("Nakshatra at 0° = Ashwini", nak["name"] == "Ashwini")
nak2 = get_nakshatra(120.5)
test("Nakshatra calculation works", nak2["name"] in [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
])

# Rashi Drishti
rd_aries = get_rashi_drishti(0)  # Movable → Fixed (except adjacent Taurus=1)
test("Aries aspects Leo(4)", 4 in rd_aries)
test("Aries aspects Scorpio(7)", 7 in rd_aries)
test("Aries aspects Aquarius(10)", 10 in rd_aries)
test("Aries does NOT aspect Taurus(1)", 1 not in rd_aries, f"Got {rd_aries}")

rd_gemini = get_rashi_drishti(2)  # Dual → other Duals
test("Gemini aspects Virgo(5)", 5 in rd_gemini)
test("Gemini aspects Sagittarius(8)", 8 in rd_gemini)
test("Gemini aspects Pisces(11)", 11 in rd_gemini)
test("Gemini does NOT aspect itself(2)", 2 not in rd_gemini)

# ═══════════════════════════════════════════════════════════════════
# 2. INTENT DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 2. INTENT DETECTION ═══")

test("Detects 'Will I get promoted?'", detect_prashna_intent("Will I get promoted?"))
test("Detects 'Should I take this job?'", detect_prashna_intent("Should I take this job?"))
test("Detects 'Is it a good time to invest?'", detect_prashna_intent("Is it a good time to invest?"))
test("Detects 'Can I trust this person?'", detect_prashna_intent("Can I trust this person?"))
test("Detects 'yes or no'", detect_prashna_intent("Give me a yes or no on this deal"))
test("Detects 'right decision'", detect_prashna_intent("Am I making the right decision?"))
test("Rejects generic question", not detect_prashna_intent("Tell me about my career"))
test("Rejects statement", not detect_prashna_intent("I want to change jobs"))

# ═══════════════════════════════════════════════════════════════════
# 3. DOMAIN DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 3. DOMAIN DETECTION ═══")

d, h = detect_domain("Will I get promoted at work?")
test("Career domain detected", d in ["career", "promotion", "promoted", "job"], f"Got {d}")
test("Career → 10th house", 10 in h, f"Got {h}")

d2, h2 = detect_domain("Should I invest in this stock?")
test("Finance domain detected", d2 in ["investment", "finance", "money", "wealth"], f"Got {d2}")
test("Finance → 2nd or 11th house", 2 in h2 or 11 in h2, f"Got {h2}")

d3, h3 = detect_domain("Will she marry me?")
test("Relationship domain detected", d3 in ["marriage", "relationship", "love", "partner"], f"Got {d3}")
test("Marriage → 7th house", 7 in h3, f"Got {h3}")

d4, h4 = detect_domain("Is this a good time for something?")
test("General fallback to 10th", 10 in h4, f"Got {h4}")

# ═══════════════════════════════════════════════════════════════════
# 4. MOCK CHART FOR SCORING TESTS
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 4. SCORING TESTS (Mock Chart) ═══")

# Create a mock chart: Leo Lagna, Jupiter in 1st, Moon in 10th
mock_chart = {
    "lagna": 135.5,
    "lagna_sign": 4,  # Leo
    "lagna_sign_name": "Leo",
    "lagna_degree": 15.5,
    "lagna_nakshatra": "Purva Phalguni",
    "cusps": [
        135.0,  # 1st: Leo
        165.0,  # 2nd: Virgo
        195.0,  # 3rd: Libra
        225.0,  # 4th: Scorpio
        255.0,  # 5th: Sagittarius
        285.0,  # 6th: Capricorn
        315.0,  # 7th: Aquarius
        345.0,  # 8th: Pisces
        15.0,   # 9th: Aries
        45.0,   # 10th: Taurus
        75.0,   # 11th: Gemini
        105.0,  # 12th: Cancer
    ],
    "planets": {
        0: {  # Sun
            "id": 0, "name": "Sun", "longitude": 140.0, "sign": 4, "sign_name": "Leo",
            "degree_in_sign": 20.0, "daily_speed": 0.98, "retrograde": False,
            "house": 1, "nakshatra": "Purva Phalguni", "nakshatra_pada": 3,
        },
        1: {  # Moon
            "id": 1, "name": "Moon", "longitude": 55.0, "sign": 1, "sign_name": "Taurus",
            "degree_in_sign": 25.0, "daily_speed": 13.2, "retrograde": False,
            "house": 10, "nakshatra": "Mrigashira", "nakshatra_pada": 1,
        },
        2: {  # Mercury
            "id": 2, "name": "Mercury", "longitude": 150.0, "sign": 5, "sign_name": "Virgo",
            "degree_in_sign": 0.0, "daily_speed": 1.5, "retrograde": False,
            "house": 2, "nakshatra": "Uttara Phalguni", "nakshatra_pada": 2,
        },
        3: {  # Venus
            "id": 3, "name": "Venus", "longitude": 200.0, "sign": 6, "sign_name": "Libra",
            "degree_in_sign": 20.0, "daily_speed": 1.2, "retrograde": False,
            "house": 3, "nakshatra": "Vishakha", "nakshatra_pada": 1,
        },
        4: {  # Mars
            "id": 4, "name": "Mars", "longitude": 260.0, "sign": 8, "sign_name": "Sagittarius",
            "degree_in_sign": 20.0, "daily_speed": 0.7, "retrograde": False,
            "house": 5, "nakshatra": "Purva Ashadha", "nakshatra_pada": 3,
        },
        5: {  # Jupiter
            "id": 5, "name": "Jupiter", "longitude": 130.0, "sign": 4, "sign_name": "Leo",
            "degree_in_sign": 10.0, "daily_speed": 0.12, "retrograde": False,
            "house": 1, "nakshatra": "Magha", "nakshatra_pada": 4,
        },
        6: {  # Saturn
            "id": 6, "name": "Saturn", "longitude": 330.0, "sign": 11, "sign_name": "Pisces",
            "degree_in_sign": 0.0, "daily_speed": 0.06, "retrograde": False,
            "house": 8, "nakshatra": "Uttara Bhadrapada", "nakshatra_pada": 2,
        },
    },
    "moon_nakshatra": "Mrigashira",
    "moon_house": 10,
    "rahu_longitude": 0.0,
    "ketu_longitude": 180.0,
}

# Step A: Lagna Strength — Jupiter in 1st house should give +25
step_a = check_lagna_strength(mock_chart)
test("Step A: Benefic influence = +25%", step_a["score"] == 25, f"Got {step_a['score']}")
test("Step A: Reason mentions a benefic", any(b in step_a["reason"] for b in ["Jupiter", "Venus", "Mercury", "Moon"]), step_a["reason"])

# Step B: Lord Connection — Leo lagna (lord=Sun in Leo/1st), career question (10th house = Taurus, lord=Venus in Libra/3rd)
step_b = check_lord_connection(mock_chart, [10])
test("Step B: Lord connection score is 0 or 25", step_b["score"] in [0, 25], f"Got {step_b}")

# Step D: Moon Validation — Moon in 10th (Upachaya)
step_d = check_moon_validation(mock_chart)
test("Step D: Moon in 10th = +15%", step_d["score"] == 15, f"Got {step_d['score']}")
test("Step D: Moon house = 10", step_d["moon_house"] == 10)

# ═══════════════════════════════════════════════════════════════════
# 5. ITHASALA TESTS
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 5. ITHASALA TESTS ═══")

# Test with known applying aspect
# Moon (fast, lon=55) moving toward Venus (slow, lon=200)
# Distance = 145° — closest Tajika aspect is 120° (dist_to_120 = 25°) — too far
# Let's create a specific test scenario
applying_chart = {
    "lagna_sign": 0,  # Aries
    "cusps": [i * 30 for i in range(12)],
    "planets": {
        1: {  # Moon (fast)
            "id": 1, "name": "Moon", "longitude": 115.0, "sign": 3, "sign_name": "Cancer",
            "degree_in_sign": 25.0, "daily_speed": 13.0, "retrograde": False, "house": 4,
        },
        3: {  # Venus (slower)
            "id": 3, "name": "Venus", "longitude": 120.0, "sign": 4, "sign_name": "Leo",
            "degree_in_sign": 0.0, "daily_speed": 1.2, "retrograde": False, "house": 5,
        },
    },
}

ith = check_ithasala(applying_chart, 1, 3)  # Moon approaching Venus conjunction
test("Ithasala: Moon applying to Venus = ithasala", ith["type"] == "ithasala", f"Got {ith}")

# Test retrograde breaks Ithasala
retro_chart = {
    "lagna_sign": 0,
    "cusps": [i * 30 for i in range(12)],
    "planets": {
        2: {  # Mercury (retrograde, moving backward)
            "id": 2, "name": "Mercury", "longitude": 65.0, "sign": 2, "sign_name": "Gemini",
            "degree_in_sign": 5.0, "daily_speed": -0.5, "retrograde": True, "house": 3,
        },
        5: {  # Jupiter
            "id": 5, "name": "Jupiter", "longitude": 70.0, "sign": 2, "sign_name": "Gemini",
            "degree_in_sign": 10.0, "daily_speed": 0.1, "retrograde": False, "house": 3,
        },
    },
}

ith_retro = check_ithasala(retro_chart, 2, 5)
test("Ithasala: Retrograde faster = ishrafa", ith_retro["type"] == "ishrafa", f"Got {ith_retro}")

# ═══════════════════════════════════════════════════════════════════
# 6. EDGE YOGA TESTS
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 6. EDGE YOGA TESTS ═══")

# Muthashila: Two planets within 1° of exact aspect
muth_chart = {
    "lagna_sign": 0,
    "cusps": [i * 30 for i in range(12)],
    "planets": {
        0: {"id": 0, "name": "Sun", "longitude": 60.5, "sign": 2, "sign_name": "Gemini",
            "degree_in_sign": 0.5, "daily_speed": 1.0, "retrograde": False, "house": 3},
        4: {"id": 4, "name": "Mars", "longitude": 60.0, "sign": 2, "sign_name": "Gemini",
            "degree_in_sign": 0.0, "daily_speed": 0.7, "retrograde": False, "house": 3},
    },
}

muth = check_muthashila(muth_chart, 0, 4)
test("Muthashila: Within 1° of conjunction = detected", muth is not None, f"Got {muth}")
if muth:
    test("Muthashila: Score = 95", muth["score"] == 95)
    test("Muthashila: Override = True", muth.get("override") == True)

# ═══════════════════════════════════════════════════════════════════
# 7. MUTUAL RECEPTION TEST
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 7. MUTUAL RECEPTION ═══")

# Mars in Sagittarius (Jupiter's sign) + Jupiter in Aries (Mars's sign)
mr_chart = {
    "planets": {
        4: {"id": 4, "name": "Mars", "longitude": 260.0, "sign": 8, "sign_name": "Sagittarius",
            "degree_in_sign": 20.0, "daily_speed": 0.7, "retrograde": False, "house": 5},
        5: {"id": 5, "name": "Jupiter", "longitude": 10.0, "sign": 0, "sign_name": "Aries",
            "degree_in_sign": 10.0, "daily_speed": 0.12, "retrograde": False, "house": 9},
    },
}

mr = check_mutual_reception(mr_chart, 4, 5)
test("Mutual Reception: Mars in Sag + Jupiter in Aries", mr["found"] == True, f"Got {mr}")
test("Mutual Reception: +15%", mr["score"] == 15)

# ═══════════════════════════════════════════════════════════════════
# 8. COOLDOWN TESTS
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 8. COOLDOWN TESTS ═══")

# No previous question
cd1 = check_cooldown(None)
test("Cooldown: None → allowed", cd1["allowed"] == True)

# Question 2 hours ago (within 24h cooldown)
two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
cd2 = check_cooldown(two_hours_ago, cooldown_hours=24)
test("Cooldown: 2h ago with 24h cooldown → blocked", cd2["allowed"] == False)
test("Cooldown: Has remaining seconds", cd2["remaining_seconds"] > 0)

# Question 25 hours ago (outside 24h cooldown)
day_ago = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
cd3 = check_cooldown(day_ago, cooldown_hours=24)
test("Cooldown: 25h ago with 24h cooldown → allowed", cd3["allowed"] == True)

# ═══════════════════════════════════════════════════════════════════
# 9. FULL VERDICT TEST (Mock Chart)
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 9. FULL VERDICT (Mock Chart) ═══")

verdict = compute_prashna_verdict(
    chart=mock_chart,
    question="Will I get promoted this year?",
    jaimini_data=None,
    natal_dasha="Mars-Moon",
)

test("Verdict has verdict field", "verdict" in verdict)
test("Verdict has score 0-100", 0 <= verdict["score"] <= 100, f"Score={verdict['score']}")
test("Verdict has label", verdict["label"] in [
    "High Confidence", "Favorable", "Moderate", "Low Confidence", "Not Supported", "Opportunity Passed"
])
test("Verdict has domain", "domain" in verdict)
test("Verdict has timing", "timing" in verdict)
test("Verdict has breakdown", "breakdown" in verdict)
test("Breakdown has 4 steps", all(k in verdict["breakdown"] for k in [
    "lagna_strength", "lord_connection", "ithasala", "moon_validation"
]))
test("Verdict has prashna_chart", "prashna_chart" in verdict)
test("Prashna chart has lagna_sign", "lagna_sign" in verdict["prashna_chart"])
test("Verdict has weakest_planet", "weakest_planet" in verdict)

print(f"\n  Verdict: {verdict['verdict']} ({verdict['score']}%) — {verdict['label']}")
print(f"  Domain: {verdict['domain']}, Timing: {verdict['timing']}")

# ═══════════════════════════════════════════════════════════════════
# 10. PROMPT BUILDER TEST
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 10. PROMPT BUILDER ═══")

prompt = build_prashna_prompt(verdict, "Will I get promoted?", "Ramandeep", "global")
test("Prompt contains VERDICT", "VERDICT:" in prompt)
test("Prompt contains SCORE", "SCORE:" in prompt)
test("Prompt contains question", "Will I get promoted?" in prompt)
test("Prompt contains user name", "Ramandeep" in prompt)
test("Prompt contains zero jargon instruction", "ZERO astrological jargon" in prompt)
test("Prompt length > 500 chars", len(prompt) > 500, f"Length={len(prompt)}")

# ═══════════════════════════════════════════════════════════════════
# 11. LIVE CHART TEST (if swisseph available)
# ═══════════════════════════════════════════════════════════════════
print("\n═══ 11. LIVE CHART CAST ═══")

try:
    import swisseph as swe_test
    # Cast chart for right now, Cliffside Park NJ (40.82, -73.99)
    now_utc = datetime.now(timezone.utc)
    chart = cast_prashna_chart(40.82, -73.99, now_utc)

    test("Live chart has lagna", "lagna" in chart)
    test("Live chart lagna_sign 0-11", 0 <= chart["lagna_sign"] <= 11, f"Got {chart['lagna_sign']}")
    test("Live chart has 12 cusps", len(chart["cusps"]) == 12)
    test("Live chart has 7 planets", len(chart["planets"]) == 7)
    test("Live chart has moon_nakshatra", chart["moon_nakshatra"] in [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
        "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
        "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha",
        "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ])

    # All planets have required fields
    for pid, pdata in chart["planets"].items():
        test(f"Planet {pdata['name']} has longitude", "longitude" in pdata)
        test(f"Planet {pdata['name']} has daily_speed", "daily_speed" in pdata)
        test(f"Planet {pdata['name']} has house 1-12", 1 <= pdata["house"] <= 12, f"Got {pdata['house']}")

    print(f"\n  📍 Chart cast for: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  🔮 Prashna Lagna: {chart['lagna_sign_name']} at {chart['lagna_degree']:.1f}°")
    print(f"  🌙 Moon: {chart['planets'][1]['sign_name']} in {chart['moon_nakshatra']} (House {chart['moon_house']})")

    # Full pipeline test
    print("\n═══ 12. FULL PIPELINE (Live) ═══")
    result = run_prashna_engine(
        question="Should I accept this job offer?",
        lat=40.82, lng=-73.99,
        timestamp=now_utc,
        natal_dasha="Mars-Moon",
        user_name="Ramandeep",
        locale="US",
    )

    test("Pipeline has verdict", "verdict" in result)
    test("Pipeline has score", "score" in result)
    test("Pipeline has claude_prompt", "claude_prompt" in result)
    test("Pipeline has cooldown_until", "cooldown_until" in result)
    test("Pipeline has full_chart", "full_chart" in result)

    print(f"\n  ⚡ VERDICT: {result['verdict']}")
    print(f"  📊 SCORE: {result['score']}% — {result['label']}")
    print(f"  🎯 DOMAIN: {result['domain']}")
    print(f"  ⏰ TIMING: {result['timing']}")
    bd = result["breakdown"]
    print(f"  Step A (Lagna): {bd['lagna_strength']['score']}%")
    print(f"  Step B (Lords): {bd['lord_connection']['score']}%")
    print(f"  Step C (Ithasala): {bd['ithasala']['score']}% ({bd['ithasala']['type']})")
    print(f"  Step D (Moon): {bd['moon_validation']['score']}%")
    if bd.get("edge_yoga"):
        print(f"  Edge Yoga: {bd['edge_yoga']['yoga']} (+{bd['edge_yoga']['score']}%)")
    if bd.get("mutual_reception", {}).get("found"):
        print(f"  Mutual Reception: +{bd['mutual_reception']['score']}%")
    print(f"  📍 Lagna: {result['prashna_chart']['lagna_sign']} at {result['prashna_chart']['lagna_degree']:.1f}°")
    print(f"  🌙 Moon: {result['prashna_chart']['moon_nakshatra']} (House {result['prashna_chart']['moon_house']})")
    sig1 = result['prashna_chart']['significator_1']
    sigx = result['prashna_chart']['significator_x']
    print(f"  You: {sig1['planet']} in {sig1['sign']} (House {sig1['house']})")
    print(f"  Goal: {sigx['planet']} in {sigx['sign']} (House {sigx['house']})")
    print(f"  💊 Weakest: {result['weakest_planet']['planet']} ({', '.join(result['weakest_planet']['reasons'])})")

except ImportError:
    print("  ⚠️  swisseph not installed — skipping live chart tests")
    print("  Install with: pip install pyswisseph")

# ═══════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════
print(f"\n{'═' * 50}")
print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
print(f"{'═' * 50}")

if failed > 0:
    sys.exit(1)
else:
    print("  🎉 ALL TESTS PASSED")
    sys.exit(0)
