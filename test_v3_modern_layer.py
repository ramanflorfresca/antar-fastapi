#!/usr/bin/env python3
"""
test_v3_modern_layer.py
========================
Retrodiction tests for v3 Modern Interpretation Layer.

Tests validate three sub-layers:
  1. Classical-to-Modern Translation (modern_translation.py)
  2. Dushthana-as-Wealth Detection (dushthana_wealth_detector.py)
  3. Lal Kitab Negations (lal_kitab_negations.py)
  4. Integration into business_fit.py v3

Celebrity charts used:
  - Bachchan: 8H stellium (Sun+Mercury+Saturn+Venus in 8H) — fame-through-crisis
  - Musk: Rahu-11H, Kemadruma, Mars-Saturn conjunction — tech-disruption billionaire
  - Dutt: 12H emphasis (Moon+Saturn in 12H), Jupiter sleeping — foreign/creative career with blocks

Plus existing Raman/Andres charts for v3 integration regression.

Usage:
    cd ~/antarai && source venv311/bin/activate
    python test_v3_modern_layer.py
"""

import sys
import json

sys.path.insert(0, ".")

from antar_engine.life_arc.modern_translation import compute_modern_corrections
from antar_engine.life_arc.dushthana_wealth_detector import detect_modern_dushthana_wealth_pattern
from antar_engine.life_arc.lal_kitab_negations import check_lal_kitab_negations
from antar_engine.life_arc.signatures.business_fit import analyze_business_fit


# ─── MOCK CHART DATA: BACHCHAN ──────────────────────────────────────────────
# Amitabh Bachchan: Libra rising (lagna sign_index=6)
# Known placements (approximate):
#   Sun in 8H (Taurus, sign 1) — fame through survival narrative
#   Mercury in 8H (Taurus, sign 1) — investigative communication
#   Saturn in 8H (Taurus, sign 1) — long-duration transformation
#   Venus in 8H (Taurus, sign 1) — dignity in own sign, creative transformation
#   Jupiter in 4H (Capricorn, sign 9) — debilitated but dikbala
#   Mars in 1H (Libra, sign 6) — debilitated lagna, drive
#   Moon in 5H (Aquarius, sign 10) — creative, no flanking planets = Kemadruma check
#   Rahu in 3H (Sagittarius, sign 8) — media/communication
#   Ketu in 9H (Gemini, sign 2)

BACHCHAN_CHART = {
    "lagna": {
        "sign_index": 6,  # Libra
        "sign": "Libra",
        "longitude": 180.0,
        "degree": 12.0,
    },
    "planets": {
        "Sun": {
            "sign_index": 1, "sign": "Taurus", "house": 8,
            "degree": 20.0, "longitude": 50.0,
            "nakshatra": "Rohini", "nakshatra_lord": "Moon",
        },
        "Moon": {
            "sign_index": 10, "sign": "Aquarius", "house": 5,
            "degree": 15.0, "longitude": 315.0,
            "nakshatra": "Shatabhisha", "nakshatra_lord": "Rahu",
        },
        "Mars": {
            "sign_index": 6, "sign": "Libra", "house": 1,
            "degree": 25.0, "longitude": 205.0,
            "nakshatra": "Vishakha", "nakshatra_lord": "Jupiter",
        },
        "Mercury": {
            "sign_index": 1, "sign": "Taurus", "house": 8,
            "degree": 10.0, "longitude": 40.0,
            "nakshatra": "Krittika", "nakshatra_lord": "Sun",
        },
        "Jupiter": {
            "sign_index": 9, "sign": "Capricorn", "house": 4,
            "degree": 5.0, "longitude": 275.0,
            "nakshatra": "Uttara Ashadha", "nakshatra_lord": "Sun",
        },
        "Venus": {
            "sign_index": 1, "sign": "Taurus", "house": 8,
            "degree": 15.0, "longitude": 45.0,
            "nakshatra": "Rohini", "nakshatra_lord": "Moon",
        },
        "Saturn": {
            "sign_index": 1, "sign": "Taurus", "house": 8,
            "degree": 28.0, "longitude": 58.0,
            "nakshatra": "Mrigashirsha", "nakshatra_lord": "Mars",
        },
        "Rahu": {
            "sign_index": 8, "sign": "Sagittarius", "house": 3,
            "degree": 18.0, "longitude": 258.0,
            "nakshatra": "Purva Ashadha", "nakshatra_lord": "Venus",
        },
        "Ketu": {
            "sign_index": 2, "sign": "Gemini", "house": 9,
            "degree": 18.0, "longitude": 78.0,
            "nakshatra": "Ardra", "nakshatra_lord": "Rahu",
        },
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {
            "lagna": "Libra", "lagna_lord": "Venus",
            "sun_hora_planets": ["Sun", "Mars", "Saturn"],
            "moon_hora_planets": ["Moon", "Mercury", "Jupiter", "Venus", "Rahu"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Aries", "planets": {}},
        "d9": {"lagna": "Aries", "planets": {}},
        "d10": {"lagna": "Cancer", "planets": {}},
        "d60": {
            "planet_analysis": {
                "Sun": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
                "Saturn": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
                "Venus": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
            },
        },
    },
    "archetype": {"name": "The Creative"},
}


# ─── MOCK CHART DATA: MUSK ─────────────────────────────────────────────────
# Elon Musk: Cancer rising (lagna sign_index=3) — approximate
# Known placements:
#   Rahu in 11H (Taurus, sign 1) — billionaire marker, unconventional network gains
#   Moon in 7H (Capricorn, sign 9) — no flanking planets = Kemadruma
#   Mars in 7H (Capricorn, sign 9) — Mars-Moon conjunction
#   Saturn in 12H (Gemini, sign 2) — foreign operations, Mars-Saturn not same sign
#   Sun in 1H (Cancer, sign 3) — identity/drive
#   Mercury in 1H (Cancer, sign 3) — business intellect
#   Jupiter in 3H (Virgo, sign 5) — entrepreneurial communication
#   Venus in 12H (Gemini, sign 2) — foreign creative wealth
#   Ketu in 5H (Scorpio, sign 7)

MUSK_CHART = {
    "lagna": {
        "sign_index": 3,  # Cancer
        "sign": "Cancer",
        "longitude": 90.0,
        "degree": 5.0,
    },
    "planets": {
        "Sun": {
            "sign_index": 3, "sign": "Cancer", "house": 1,
            "degree": 28.0, "longitude": 118.0,
            "nakshatra": "Ashlesha", "nakshatra_lord": "Mercury",
        },
        "Moon": {
            "sign_index": 9, "sign": "Capricorn", "house": 7,
            "degree": 8.0, "longitude": 278.0,
            "nakshatra": "Uttara Ashadha", "nakshatra_lord": "Sun",
        },
        "Mars": {
            "sign_index": 9, "sign": "Capricorn", "house": 7,
            "degree": 22.0, "longitude": 292.0,
            "nakshatra": "Shravana", "nakshatra_lord": "Moon",
        },
        "Mercury": {
            "sign_index": 3, "sign": "Cancer", "house": 1,
            "degree": 15.0, "longitude": 105.0,
            "nakshatra": "Pushya", "nakshatra_lord": "Saturn",
        },
        "Jupiter": {
            "sign_index": 5, "sign": "Virgo", "house": 3,
            "degree": 12.0, "longitude": 162.0,
            "nakshatra": "Hasta", "nakshatra_lord": "Moon",
        },
        "Venus": {
            "sign_index": 2, "sign": "Gemini", "house": 12,
            "degree": 20.0, "longitude": 80.0,
            "nakshatra": "Punarvasu", "nakshatra_lord": "Jupiter",
        },
        "Saturn": {
            "sign_index": 2, "sign": "Gemini", "house": 12,
            "degree": 5.0, "longitude": 65.0,
            "nakshatra": "Mrigashirsha", "nakshatra_lord": "Mars",
        },
        "Rahu": {
            "sign_index": 1, "sign": "Taurus", "house": 11,
            "degree": 15.0, "longitude": 45.0,
            "nakshatra": "Rohini", "nakshatra_lord": "Moon",
        },
        "Ketu": {
            "sign_index": 7, "sign": "Scorpio", "house": 5,
            "degree": 15.0, "longitude": 225.0,
            "nakshatra": "Anuradha", "nakshatra_lord": "Saturn",
        },
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {
            "lagna": "Cancer", "lagna_lord": "Moon",
            "sun_hora_planets": ["Sun", "Mars", "Saturn", "Rahu"],
            "moon_hora_planets": ["Moon", "Mercury", "Jupiter", "Venus"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Aries", "planets": {}},
        "d9": {"lagna": "Aries", "planets": {}},
        "d10": {"lagna": "Aries", "planets": {}},
        "d60": {
            "planet_analysis": {
                "Rahu": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
                "Mars": {"karma_name": "Manushya", "karma_desc": "human karma", "is_positive": True, "is_challenging": False},
            },
        },
    },
    "archetype": {"name": "The Visionary"},
}


# ─── MOCK CHART DATA: DUTT ──────────────────────────────────────────────────
# Sanjay Dutt: Sagittarius rising (lagna sign_index=8) — approximate
# Known placements:
#   Moon in 12H (Scorpio, sign 7) — foreign/behind-scenes emotional life
#   Saturn in 12H (Scorpio, sign 7) — structured foreign presence
#   Jupiter in 6H (Taurus, sign 1) — sleeping planet (dusthana, no benefic aspect)
#   Sun in 9H (Leo, sign 4) — authority through dharma
#   Mars in 10H (Virgo, sign 5) — career action
#   Mercury in 9H (Leo, sign 4) — communication through dharma
#   Venus in 10H (Virgo, sign 5) — creative career
#   Rahu in 2H (Capricorn, sign 9) — unconventional wealth
#   Ketu in 8H (Cancer, sign 3)

DUTT_CHART = {
    "lagna": {
        "sign_index": 8,  # Sagittarius
        "sign": "Sagittarius",
        "longitude": 240.0,
        "degree": 10.0,
    },
    "planets": {
        "Sun": {
            "sign_index": 4, "sign": "Leo", "house": 9,
            "degree": 12.0, "longitude": 132.0,
            "nakshatra": "Magha", "nakshatra_lord": "Ketu",
        },
        "Moon": {
            "sign_index": 7, "sign": "Scorpio", "house": 12,
            "degree": 20.0, "longitude": 230.0,
            "nakshatra": "Jyeshtha", "nakshatra_lord": "Mercury",
        },
        "Mars": {
            "sign_index": 5, "sign": "Virgo", "house": 10,
            "degree": 15.0, "longitude": 165.0,
            "nakshatra": "Hasta", "nakshatra_lord": "Moon",
        },
        "Mercury": {
            "sign_index": 4, "sign": "Leo", "house": 9,
            "degree": 25.0, "longitude": 145.0,
            "nakshatra": "Purva Phalguni", "nakshatra_lord": "Venus",
        },
        "Jupiter": {
            "sign_index": 1, "sign": "Taurus", "house": 6,
            "degree": 10.0, "longitude": 40.0,
            "nakshatra": "Krittika", "nakshatra_lord": "Sun",
        },
        "Venus": {
            "sign_index": 5, "sign": "Virgo", "house": 10,
            "degree": 8.0, "longitude": 158.0,
            "nakshatra": "Uttara Phalguni", "nakshatra_lord": "Sun",
        },
        "Saturn": {
            "sign_index": 7, "sign": "Scorpio", "house": 12,
            "degree": 10.0, "longitude": 220.0,
            "nakshatra": "Anuradha", "nakshatra_lord": "Saturn",
        },
        "Rahu": {
            "sign_index": 9, "sign": "Capricorn", "house": 2,
            "degree": 5.0, "longitude": 275.0,
            "nakshatra": "Uttara Ashadha", "nakshatra_lord": "Sun",
        },
        "Ketu": {
            "sign_index": 3, "sign": "Cancer", "house": 8,
            "degree": 5.0, "longitude": 95.0,
            "nakshatra": "Pushya", "nakshatra_lord": "Saturn",
        },
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {
            "lagna": "Sagittarius", "lagna_lord": "Jupiter",
            "sun_hora_planets": ["Sun", "Mars", "Jupiter"],
            "moon_hora_planets": ["Moon", "Mercury", "Venus", "Saturn"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Aries", "planets": {}},
        "d9": {"lagna": "Aries", "planets": {}},
        "d10": {"lagna": "Aries", "planets": {}},
        "d60": {
            "planet_analysis": {
                "Jupiter": {"karma_name": "Bhrashta", "karma_desc": "fallen karma", "is_positive": False, "is_challenging": True},
            },
        },
    },
    "archetype": {"name": "The Warrior"},
}


# ─── RAMAN CHART (from v2 tests) ────────────────────────────────────────────
RAMAN_CHART = {
    "lagna": {"sign_index": 9, "sign": "Capricorn", "longitude": 280.0, "degree": 10.0},
    "planets": {
        "Sun":     {"sign_index": 7, "sign": "Scorpio",   "house": 11, "degree": 15.0, "longitude": 225.0},
        "Moon":    {"sign_index": 11,"sign": "Pisces",     "house": 3,  "degree": 28.0, "longitude": 358.0},
        "Mars":    {"sign_index": 6, "sign": "Libra",      "house": 10, "degree": 20.0, "longitude": 200.0},
        "Mercury": {"sign_index": 6, "sign": "Libra",      "house": 10, "degree": 5.0,  "longitude": 185.0},
        "Jupiter": {"sign_index": 10,"sign": "Aquarius",   "house": 2,  "degree": 12.0, "longitude": 312.0},
        "Venus":   {"sign_index": 7, "sign": "Scorpio",    "house": 11, "degree": 10.0, "longitude": 220.0},
        "Saturn":  {"sign_index": 2, "sign": "Gemini",     "house": 6,  "degree": 18.0, "longitude": 78.0},
        "Rahu":    {"sign_index": 7, "sign": "Scorpio",    "house": 11, "degree": 22.0, "longitude": 232.0},
        "Ketu":    {"sign_index": 1, "sign": "Taurus",     "house": 5,  "degree": 22.0, "longitude": 52.0},
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {"lagna": "Cancer", "lagna_lord": "Moon",
               "sun_hora_planets": ["Mars", "Saturn"],
               "moon_hora_planets": ["Sun", "Moon", "Mercury", "Jupiter", "Venus", "Rahu"],
               "wealth_signals": []},
        "d4": {"planets": {"Jupiter": {"sign_index": 3, "house": 7}, "Venus": {"sign_index": 0, "house": 4},
                           "Mars": {"sign_index": 9, "house": 1}, "Saturn": {"sign_index": 6, "house": 10}}},
        "d7": {"lagna": "Aries", "planets": {"Jupiter": {"sign_index": 8, "house": 6},
                                              "Venus": {"sign_index": 1, "house": 11},
                                              "Mars": {"sign_index": 0, "house": 1}}},
        "d9": {"lagna": "Cancer", "planets": {"Jupiter": {"sign_index": 8, "house": 6},
                                               "Mercury": {"sign_index": 5, "house": 12},
                                               "Venus": {"sign_index": 3, "house": 10},
                                               "Sun": {"sign_index": 11, "house": 6}}},
        "d10": {"lagna": "Scorpio", "planets": {
            "Mercury": {"sign_index": 6, "sign": "Libra", "house": 10},
            "Jupiter": {"sign_index": 10, "sign": "Aquarius", "house": 4},
            "Venus": {"sign_index": 7, "sign": "Scorpio", "house": 1},
            "Mars": {"sign_index": 0, "sign": "Aries", "house": 6},
            "Saturn": {"sign_index": 2, "sign": "Gemini", "house": 8}}},
        "d60": {"planet_analysis": {
            "Mercury": {"karma_name": "Bhrashta", "karma_desc": "fallen karma", "is_positive": False, "is_challenging": True},
            "Jupiter": {"karma_name": "Bhrashta", "karma_desc": "fallen karma", "is_positive": False, "is_challenging": True},
            "Saturn": {"karma_name": "Rakshasa", "karma_desc": "demonic karma", "is_positive": False, "is_challenging": True},
            "Sun": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
            "Moon": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
            "Venus": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
            "Mars": {"karma_name": "Manushya", "karma_desc": "human karma", "is_positive": True, "is_challenging": False}}},
    },
    "archetype": {"name": "The Broker"},
}


# ─── TEST FUNCTIONS ─────────────────────────────────────────────────────────

passed = 0
failed = 0
total = 0


def check(test_name: str, condition: bool, detail: str = ""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✅ Test {total}: {test_name}")
    else:
        failed += 1
        print(f"  ❌ Test {total}: {test_name}")
        if detail:
            print(f"      Detail: {detail}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: MODERN TRANSLATION LAYER
# ═══════════════════════════════════════════════════════════════════════════

print("\n╔═══════════════════════════════════════════════════════════════╗")
print("║  v3 TEST SUITE: Modern Interpretation Layer                  ║")
print("╚═══════════════════════════════════════════════════════════════╝\n")

print("── Section 1: Classical-to-Modern Translation ──\n")

# Test 1: Bachchan — 8H stellium should produce large positive modern correction
bachchan_corrections = compute_modern_corrections(BACHCHAN_CHART)
correction_keys = [c["key"] for c in bachchan_corrections["corrections"]]
check(
    "Bachchan: 8H stellium detected in modern corrections",
    "sun_8h" in correction_keys and "saturn_8h" in correction_keys,
    f"Keys found: {correction_keys}"
)

# Test 2: Bachchan — net adjustment should be strongly positive (classical negative → modern positive)
check(
    "Bachchan: net modern adjustment > +5.0 (8H stellium classical→modern lift)",
    bachchan_corrections["net_adjustment"] > 5.0,
    f"Net adjustment: {bachchan_corrections['net_adjustment']}"
)

# Test 3: Musk — Rahu-11H should be detected with modern score 5.0
musk_corrections = compute_modern_corrections(MUSK_CHART)
rahu_11h_found = [c for c in musk_corrections["corrections"] if c["key"] == "rahu_11h"]
check(
    "Musk: Rahu-11H detected with modern_score=5.0",
    len(rahu_11h_found) == 1 and rahu_11h_found[0]["modern_score"] == 5.0,
    f"Rahu-11H entries: {rahu_11h_found}"
)

# Test 4: Musk — Kemadruma should be detected
kemadruma_found = [c for c in musk_corrections["corrections"] if c["key"] == "kemadruma"]
check(
    "Musk: Kemadruma detected (Moon in Capricorn, no flanking planets)",
    len(kemadruma_found) == 1,
    f"Kemadruma entries: {kemadruma_found}"
)

# Test 5: Dutt — 12H placements should trigger modern corrections
dutt_corrections = compute_modern_corrections(DUTT_CHART)
correction_keys = [c["key"] for c in dutt_corrections["corrections"]]
check(
    "Dutt: Rahu-2H detected in modern corrections",
    "rahu_2h" in correction_keys,
    f"Keys found: {correction_keys}"
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: DUSHTHANA-AS-WEALTH DETECTION
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Section 2: Dushthana-as-Wealth Detection ──\n")

# Test 6: Bachchan — 8H_TRANSFORMATION_WEALTH should be strongest pattern
bachchan_dushthana = detect_modern_dushthana_wealth_pattern(BACHCHAN_CHART)
check(
    "Bachchan: 8H_TRANSFORMATION_WEALTH is strongest dushthana pattern",
    bachchan_dushthana["strongest_pattern"] == "8H_TRANSFORMATION_WEALTH",
    f"Strongest: {bachchan_dushthana['strongest_pattern']}"
)

# Test 7: Bachchan — 8H strength should be very high (4-planet stellium)
p8_result = [p for p in bachchan_dushthana["patterns_detected"]
             if p["pattern"] == "8H_TRANSFORMATION_WEALTH"][0]
check(
    "Bachchan: 8H_TRANSFORMATION_WEALTH strength >= 8.0 (stellium + multiple activators)",
    p8_result["strength"] >= 8.0,
    f"Strength: {p8_result['strength']}"
)

# Test 8: Musk — 12H_FOREIGN_DIGITAL_WEALTH should be detected (Venus+Saturn in 12H)
musk_dushthana = detect_modern_dushthana_wealth_pattern(MUSK_CHART)
p12_result = [p for p in musk_dushthana["patterns_detected"]
              if p["pattern"] == "12H_FOREIGN_DIGITAL_WEALTH"][0]
check(
    "Musk: 12H_FOREIGN_DIGITAL_WEALTH detected (Venus+Saturn in 12H)",
    p12_result["detected"] and p12_result["strength"] >= 3.0,
    f"Detected: {p12_result['detected']}, Strength: {p12_result['strength']}"
)

# Test 9: Raman — 6H_ENTREPRENEUR should be detected (Saturn yogakaraka in 6H)
raman_dushthana = detect_modern_dushthana_wealth_pattern(RAMAN_CHART)
p6_result = [p for p in raman_dushthana["patterns_detected"]
             if p["pattern"] == "6H_ENTREPRENEUR"][0]
check(
    "Raman: 6H_ENTREPRENEUR detected (Saturn yogakaraka in 6H)",
    p6_result["detected"] and p6_result["strength"] >= 4.0,
    f"Detected: {p6_result['detected']}, Strength: {p6_result['strength']}"
)

# Test 10: Dutt — 12H_FOREIGN_DIGITAL_WEALTH should be detected (Moon+Saturn in 12H)
dutt_dushthana = detect_modern_dushthana_wealth_pattern(DUTT_CHART)
p12_dutt = [p for p in dutt_dushthana["patterns_detected"]
            if p["pattern"] == "12H_FOREIGN_DIGITAL_WEALTH"][0]
check(
    "Dutt: 12H_FOREIGN_DIGITAL_WEALTH detected (Moon+Saturn in 12H)",
    p12_dutt["detected"] and p12_dutt["strength"] >= 2.0,
    f"Detected: {p12_dutt['detected']}, Strength: {p12_dutt['strength']}"
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: LAL KITAB NEGATIONS
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Section 3: Lal Kitab Negations ──\n")

# Test 11: Dutt — Jupiter in 6H is NOT sleeping (Moon in H12 = 7th aspect provides benefic support)
# This validates the correct LK logic: benefic aspect rescues a sleeping planet
dutt_lk = check_lal_kitab_negations(DUTT_CHART)
sleeping_planets = [sp["planet"] for sp in dutt_lk["sleeping_planets"]]
check(
    "Dutt: Jupiter in 6H NOT sleeping (Moon in H12 aspects it from 7th)",
    "Jupiter" not in sleeping_planets,
    f"Sleeping planets: {sleeping_planets}"
)

# Test 12: Dutt — Saturn in 12H should be sleeping (no benefic in H12 except Moon,
# but Moon IS in H12 same-house — so Saturn has benefic support and is NOT sleeping either)
# Instead test that enemy-house conditions flag categories
check(
    "Dutt: LK has_warnings is True (enemy houses or other conditions detected)",
    dutt_lk["has_warnings"],
    f"has_warnings: {dutt_lk['has_warnings']}, enemies: {[e['planet'] for e in dutt_lk['enemy_houses']]}"
)

# Test 13: Raman — enemy house: Jupiter in Aquarius (Saturn-ruled, Jupiter's enemy)
raman_lk = check_lal_kitab_negations(RAMAN_CHART)
enemy_planets = [e["planet"] for e in raman_lk["enemy_houses"]]
check(
    "Raman: Jupiter in Aquarius (enemy sign) detected",
    "Jupiter" in enemy_planets,
    f"Enemy-house planets: {enemy_planets}"
)

# Test 14: Musk — LK negations should have warnings
musk_lk = check_lal_kitab_negations(MUSK_CHART)
check(
    "Musk: has_warnings is True (at least some LK conditions active)",
    musk_lk["has_warnings"],
    f"has_warnings: {musk_lk['has_warnings']}, sleeping: {[sp['planet'] for sp in musk_lk['sleeping_planets']]}, enemies: {[e['planet'] for e in musk_lk['enemy_houses']]}"
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: INTEGRATION — analyze_business_fit v3
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Section 4: business_fit.py v3 Integration ──\n")

# Test 15: Raman v3 — analyze_business_fit returns modern_corrections key
raman_result = analyze_business_fit(RAMAN_CHART)
check(
    "Raman v3: analyze_business_fit returns 'modern_corrections' key",
    "modern_corrections" in raman_result,
    f"Keys: {list(raman_result.keys())}"
)

# Test 16: Raman v3 — analyze_business_fit returns dushthana_wealth key
check(
    "Raman v3: analyze_business_fit returns 'dushthana_wealth' key",
    "dushthana_wealth" in raman_result,
    f"Keys: {list(raman_result.keys())}"
)

# Test 17: Raman v3 — analyze_business_fit returns lk_negations key
check(
    "Raman v3: analyze_business_fit returns 'lk_negations' key",
    "lk_negations" in raman_result,
    f"Keys: {list(raman_result.keys())}"
)

# Test 18: Raman v3 — signature_version is "3.0" (updated to 4.0 after v4)
check(
    "Raman v3: signature_version is '4.0' (bumped in v4)",
    raman_result.get("signature_version") == "4.0",
    f"Version: {raman_result.get('signature_version')}"
)

# Test 19: Raman v3 — category results have lk_warnings field
all_categories = (
    raman_result.get("favored_categories", []) +
    raman_result.get("neutral_categories", []) +
    raman_result.get("disfavored_categories", [])
)
all_have_lk = all(("lk_warnings" in c) for c in all_categories)
check(
    "Raman v3: all category results have 'lk_warnings' field",
    all_have_lk and len(all_categories) == 9,
    f"Categories: {len(all_categories)}, all have lk_warnings: {all_have_lk}"
)

# Test 20: Bachchan v3 — full integration produces expected structure
bachchan_result = analyze_business_fit(BACHCHAN_CHART)
check(
    "Bachchan v3: full integration runs without error, returns all v3 keys",
    all(k in bachchan_result for k in ("modern_corrections", "dushthana_wealth", "lk_negations")),
    f"Keys: {list(bachchan_result.keys())}"
)

# Test 21: Musk v3 — full integration
musk_result = analyze_business_fit(MUSK_CHART)
check(
    "Musk v3: full integration runs, dushthana_wealth.any_detected is True",
    musk_result.get("dushthana_wealth", {}).get("any_detected") is True,
    f"any_detected: {musk_result.get('dushthana_wealth', {}).get('any_detected')}"
)

# Test 22: Raman v3 regression — v2 fields still present
check(
    "Raman v3 regression: primary_activation still present (v2 feature)",
    "primary_activation" in raman_result and raman_result["primary_activation"] is not None,
    f"primary_activation: {raman_result.get('primary_activation')}"
)

# Test 23: Raman v3 regression — favored categories still scored correctly
favored_names = [c["category"] for c in raman_result.get("favored_categories", [])]
check(
    "Raman v3 regression: PLATFORM and SERVICE_MASSES_AUTOMATION still favored",
    "PLATFORM" in favored_names and "SERVICE_MASSES_AUTOMATION" in favored_names,
    f"Favored: {favored_names}"
)


# ─── SUMMARY ────────────────────────────────────────────────────────────────

print(f"\n{'═' * 60}")
print(f"  v3 Modern Layer Tests: {passed}/{total} passed, {failed} failed")
print(f"{'═' * 60}")

if failed > 0:
    print("\n⚠️  Some tests failed. Review the output above.")
    sys.exit(1)
else:
    print("\n🎉 All v3 tests passed!")
    sys.exit(0)
