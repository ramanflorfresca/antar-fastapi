#!/usr/bin/env python3
"""
test_v4_archetypes.py
======================
Retrodiction tests for v4 Archetype Classification + Detection layer.

Tests validate:
  1. Viparita stack detection (v4_detections.py)
  2. Identity-overwhelm detection (v4_detections.py)
  3. Moon MD H2 pressure detection (v4_detections.py)
  4. D-2 hora business mismatch (v4_detections.py)
  5. Archetype classification (archetype_classifier.py)
  6. v4 integration into business_fit.py

Charts used:
  - MUSK: Cancer rising — triple Viparita, crisis-engine → DISRUPTOR
  - GATES: Gemini rising — Mahapurusha stacking, Saturn structure → SYSTEMATIC
  - MASS_SERVER_CHART: Virgo rising — Saturn in H6, Rahu H10 → MASS_SERVER
  - SHASHI: Libra rising — H1 stellium without output → CHARISMA
  - ANDRES: Cancer rising — Jupiter+Saturn kendras → INSTITUTIONAL
  - RAMAN: Capricorn rising — regression check

Usage:
    cd ~/antarai && source venv311/bin/activate
    python test_v4_archetypes.py
"""

import sys
import json

sys.path.insert(0, ".")

from antar_engine.life_arc.v4_detections import (
    detect_viparita_stack,
    detect_identity_overwhelm,
    check_moon_md_h2_pressure,
    check_d2_hora_business_mismatch,
)
from antar_engine.life_arc.archetype_classifier import (
    classify_wealth_archetype,
    WEALTH_ARCHETYPES,
)
from antar_engine.life_arc.signatures.business_fit import (
    analyze_business_fit,
    detect_yogakaraka_activation,
    detect_mahapurusha_stack,
)


# ═══════════════════════════════════════════════════════════════════════════
# MOCK CHART DATA
# ═══════════════════════════════════════════════════════════════════════════

# ─── MUSK: Cancer rising — triple Viparita (6L in 12, 8L in 6, 12L in 8)
# 6L = Jupiter (Sagittarius lord for Cancer 6H) in H12
# 8L = Saturn (Aquarius lord for Cancer 8H) in H12
# 12L = Mercury (Gemini lord for Cancer 12H) in H1
# Approximate chart: crisis-engine architecture
MUSK_CHART = {
    "lagna": {"sign_index": 3, "sign": "Cancer", "longitude": 90.0, "degree": 5.0},
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
    "yogas": [
        # Pre-computed viparita yogas for Musk
        {"name": "Viparita (6L in 12H)", "category": "viparita", "strength": "strong"},
        {"name": "Viparita (8L in 12H)", "category": "viparita", "strength": "strong"},
        {"name": "Viparita (12L in 8H)", "category": "viparita", "strength": "strong"},
    ],
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
            },
        },
    },
    "archetype": {"name": "The Visionary"},
}


# ─── GATES: Gemini rising — Mahapurusha stacking (Bhadra + Sasa)
# Mercury in own sign Gemini H1 (Bhadra), Saturn own sign Capricorn H8
# Actually for SYSTEMATIC we need Saturn in kendra. Let's adjust:
# Gemini rising: Mercury own sign H1 (Bhadra), Saturn exalted Libra H5
# Better: use a chart where Saturn is in kendra.
# Virgo rising: Mercury own sign H1 (Bhadra), Saturn own Aquarius H6 — no, H6 not kendra
# Taurus rising: Saturn yogakaraka, rules 9H+10H.
# Saturn in Aquarius (own) H10 = Sasa, Mercury in Virgo (own) H5 — not kendra
# Let's use: Libra rising (Saturn yogakaraka for Libra)
# Saturn exalted Libra H1 (Sasa), Jupiter own sign Sagittarius H3 — nope
# Simplest: Cancer rising like Andres but with different emphasis
# Actually let's just make Gates Gemini rising with pre-computed yogas
GATES_CHART = {
    "lagna": {"sign_index": 2, "sign": "Gemini", "longitude": 60.0, "degree": 12.0},
    "planets": {
        "Sun": {
            "sign_index": 6, "sign": "Libra", "house": 5,
            "degree": 18.0, "longitude": 198.0,
            "nakshatra": "Swati", "nakshatra_lord": "Rahu",
        },
        "Moon": {
            "sign_index": 11, "sign": "Pisces", "house": 10,
            "degree": 10.0, "longitude": 340.0,
            "nakshatra": "Uttara Bhadrapada", "nakshatra_lord": "Saturn",
        },
        "Mars": {
            "sign_index": 5, "sign": "Virgo", "house": 4,
            "degree": 5.0, "longitude": 155.0,
            "nakshatra": "Uttara Phalguni", "nakshatra_lord": "Sun",
        },
        "Mercury": {
            "sign_index": 5, "sign": "Virgo", "house": 4,
            "degree": 22.0, "longitude": 172.0,
            "nakshatra": "Hasta", "nakshatra_lord": "Moon",
        },
        "Jupiter": {
            "sign_index": 3, "sign": "Cancer", "house": 2,
            "degree": 8.0, "longitude": 98.0,
            "nakshatra": "Pushya", "nakshatra_lord": "Saturn",
        },
        "Venus": {
            "sign_index": 6, "sign": "Libra", "house": 5,
            "degree": 3.0, "longitude": 183.0,
            "nakshatra": "Chitra", "nakshatra_lord": "Mars",
        },
        "Saturn": {
            "sign_index": 10, "sign": "Aquarius", "house": 9,
            "degree": 5.0, "longitude": 305.0,
            "nakshatra": "Dhanishta", "nakshatra_lord": "Mars",
        },
        "Rahu": {
            "sign_index": 8, "sign": "Sagittarius", "house": 7,
            "degree": 20.0, "longitude": 260.0,
            "nakshatra": "Purva Ashadha", "nakshatra_lord": "Venus",
        },
        "Ketu": {
            "sign_index": 2, "sign": "Gemini", "house": 1,
            "degree": 20.0, "longitude": 80.0,
            "nakshatra": "Punarvasu", "nakshatra_lord": "Jupiter",
        },
    },
    "yogas": [
        # Bhadra: Mercury in own sign Virgo in H4 (kendra)
        {"name": "Bhadra", "category": "mahapurusha", "planet": "Mercury", "strength": "strong",
         "description": "Mercury in own sign Virgo in 4th house"},
        # Sasa: We need Saturn in kendra for this to work properly
        # Saturn in Aquarius H9 is NOT kendra, so let's only give Bhadra
        # and add systematic strength through other means
    ],
    "divisional_charts": {
        "d2": {
            "lagna": "Gemini", "lagna_lord": "Mercury",
            "sun_hora_planets": ["Sun", "Mars", "Saturn", "Rahu", "Jupiter"],
            "moon_hora_planets": ["Moon", "Mercury", "Venus", "Ketu"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Cancer", "planets": {}},
        "d9": {
            "lagna": "Taurus",
            "planets": {
                "Saturn": {"sign_index": 10, "house": 10},  # dignified in navamsha
            },
        },
        "d10": {
            "lagna": "Virgo",
            "planets": {
                "Mercury": {"sign_index": 5, "sign": "Virgo", "house": 1},
                "Saturn": {"sign_index": 10, "sign": "Aquarius", "house": 6},
                "Jupiter": {"sign_index": 3, "sign": "Cancer", "house": 11},
            },
        },
        "d60": {
            "planet_analysis": {
                "Mercury": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
                "Saturn": {"karma_name": "Deva", "karma_desc": "divine karma", "is_positive": True, "is_challenging": False},
            },
        },
    },
    "archetype": {"name": "The Architect"},
}


# ─── MASS SERVER CHART: Virgo rising — Saturn dignified in H6, Rahu in H10
MASS_SERVER_CHART = {
    "lagna": {"sign_index": 5, "sign": "Virgo", "longitude": 150.0, "degree": 8.0},
    "planets": {
        "Sun": {
            "sign_index": 8, "sign": "Sagittarius", "house": 4,
            "degree": 12.0, "longitude": 252.0,
            "nakshatra": "Mula", "nakshatra_lord": "Ketu",
        },
        "Moon": {
            "sign_index": 2, "sign": "Gemini", "house": 10,
            "degree": 18.0, "longitude": 78.0,
            "nakshatra": "Ardra", "nakshatra_lord": "Rahu",
        },
        "Mars": {
            "sign_index": 10, "sign": "Aquarius", "house": 6,
            "degree": 15.0, "longitude": 315.0,
            "nakshatra": "Shatabhisha", "nakshatra_lord": "Rahu",
        },
        "Mercury": {
            "sign_index": 5, "sign": "Virgo", "house": 1,
            "degree": 20.0, "longitude": 170.0,
            "nakshatra": "Hasta", "nakshatra_lord": "Moon",
        },
        "Jupiter": {
            "sign_index": 8, "sign": "Sagittarius", "house": 4,
            "degree": 25.0, "longitude": 265.0,
            "nakshatra": "Purva Ashadha", "nakshatra_lord": "Venus",
        },
        "Venus": {
            "sign_index": 9, "sign": "Capricorn", "house": 5,
            "degree": 10.0, "longitude": 280.0,
            "nakshatra": "Uttara Ashadha", "nakshatra_lord": "Sun",
        },
        "Saturn": {
            "sign_index": 10, "sign": "Aquarius", "house": 6,
            "degree": 8.0, "longitude": 308.0,
            "nakshatra": "Dhanishta", "nakshatra_lord": "Mars",
        },
        "Rahu": {
            "sign_index": 2, "sign": "Gemini", "house": 10,
            "degree": 22.0, "longitude": 82.0,
            "nakshatra": "Punarvasu", "nakshatra_lord": "Jupiter",
        },
        "Ketu": {
            "sign_index": 8, "sign": "Sagittarius", "house": 4,
            "degree": 22.0, "longitude": 262.0,
            "nakshatra": "Purva Ashadha", "nakshatra_lord": "Venus",
        },
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {
            "lagna": "Virgo", "lagna_lord": "Mercury",
            "sun_hora_planets": ["Sun", "Mars", "Saturn"],
            "moon_hora_planets": ["Moon", "Mercury", "Jupiter", "Venus", "Rahu", "Ketu"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Taurus", "planets": {}},
        "d9": {"lagna": "Pisces", "planets": {}},
        "d10": {"lagna": "Gemini", "planets": {}},
        "d60": {"planet_analysis": {}},
    },
    "archetype": {"name": "The Servant-Leader"},
}


# ─── SHASHI (Tharoor-like): Libra rising — H1 stellium, no output engine
# 4 planets in H1 (Sun, Mercury, Venus, Jupiter), but no Saturn/Mars in H6/H10/H11
SHASHI_CHART = {
    "lagna": {"sign_index": 6, "sign": "Libra", "longitude": 180.0, "degree": 15.0},
    "planets": {
        "Sun": {
            "sign_index": 6, "sign": "Libra", "house": 1,
            "degree": 10.0, "longitude": 190.0,
            "nakshatra": "Swati", "nakshatra_lord": "Rahu",
        },
        "Moon": {
            "sign_index": 3, "sign": "Cancer", "house": 10,
            "degree": 12.0, "longitude": 102.0,
            "nakshatra": "Pushya", "nakshatra_lord": "Saturn",
        },
        "Mars": {
            "sign_index": 8, "sign": "Sagittarius", "house": 3,
            "degree": 8.0, "longitude": 248.0,
            "nakshatra": "Mula", "nakshatra_lord": "Ketu",
        },
        "Mercury": {
            "sign_index": 6, "sign": "Libra", "house": 1,
            "degree": 22.0, "longitude": 202.0,
            "nakshatra": "Vishakha", "nakshatra_lord": "Jupiter",
        },
        "Jupiter": {
            "sign_index": 6, "sign": "Libra", "house": 1,
            "degree": 5.0, "longitude": 185.0,
            "nakshatra": "Chitra", "nakshatra_lord": "Mars",
        },
        "Venus": {
            "sign_index": 6, "sign": "Libra", "house": 1,
            "degree": 18.0, "longitude": 198.0,
            "nakshatra": "Swati", "nakshatra_lord": "Rahu",
        },
        "Saturn": {
            "sign_index": 0, "sign": "Aries", "house": 7,
            "degree": 15.0, "longitude": 15.0,
            "nakshatra": "Bharani", "nakshatra_lord": "Venus",
        },
        "Rahu": {
            "sign_index": 10, "sign": "Aquarius", "house": 5,
            "degree": 8.0, "longitude": 308.0,
            "nakshatra": "Dhanishta", "nakshatra_lord": "Mars",
        },
        "Ketu": {
            "sign_index": 4, "sign": "Leo", "house": 11,
            "degree": 8.0, "longitude": 128.0,
            "nakshatra": "Magha", "nakshatra_lord": "Ketu",
        },
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {
            "lagna": "Libra", "lagna_lord": "Venus",
            "sun_hora_planets": ["Sun", "Mars"],
            "moon_hora_planets": ["Moon", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Scorpio", "planets": {}},
        "d9": {"lagna": "Gemini", "planets": {}},
        "d10": {"lagna": "Capricorn", "planets": {}},
        "d60": {"planet_analysis": {}},
    },
    "archetype": {"name": "The Diplomat"},
}


# ─── ANDRES: Cancer rising — Jupiter+Saturn in kendras = INSTITUTIONAL
ANDRES_CHART = {
    "lagna": {"sign_index": 3, "sign": "Cancer", "longitude": 100.0, "degree": 10.0},
    "planets": {
        "Sun": {
            "sign_index": 0, "sign": "Aries", "house": 10,
            "degree": 12.0, "longitude": 12.0,
            "nakshatra": "Ashvini", "nakshatra_lord": "Ketu",
        },
        "Moon": {
            "sign_index": 3, "sign": "Cancer", "house": 1,
            "degree": 15.0, "longitude": 105.0,
            "nakshatra": "Pushya", "nakshatra_lord": "Saturn",
        },
        "Mars": {
            "sign_index": 4, "sign": "Leo", "house": 2,
            "degree": 8.0, "longitude": 128.0,
            "nakshatra": "Magha", "nakshatra_lord": "Ketu",
        },
        "Mercury": {
            "sign_index": 11, "sign": "Pisces", "house": 9,
            "degree": 20.0, "longitude": 350.0,
            "nakshatra": "Revati", "nakshatra_lord": "Mercury",
        },
        "Jupiter": {
            "sign_index": 3, "sign": "Cancer", "house": 1,
            "degree": 22.0, "longitude": 112.0,
            "nakshatra": "Ashlesha", "nakshatra_lord": "Mercury",
        },
        "Venus": {
            "sign_index": 0, "sign": "Aries", "house": 10,
            "degree": 5.0, "longitude": 5.0,
            "nakshatra": "Ashvini", "nakshatra_lord": "Ketu",
        },
        "Saturn": {
            "sign_index": 9, "sign": "Capricorn", "house": 7,
            "degree": 25.0, "longitude": 295.0,
            "nakshatra": "Dhanishta", "nakshatra_lord": "Mars",
        },
        "Rahu": {
            "sign_index": 5, "sign": "Virgo", "house": 3,
            "degree": 10.0, "longitude": 160.0,
            "nakshatra": "Hasta", "nakshatra_lord": "Moon",
        },
        "Ketu": {
            "sign_index": 11, "sign": "Pisces", "house": 9,
            "degree": 10.0, "longitude": 340.0,
            "nakshatra": "Uttara Bhadrapada", "nakshatra_lord": "Saturn",
        },
    },
    "yogas": [
        {"name": "Hamsa", "category": "mahapurusha", "planet": "Jupiter", "strength": "strong",
         "description": "Jupiter exalted in Cancer in 1st house"},
        {"name": "Sasa", "category": "mahapurusha", "planet": "Saturn", "strength": "strong",
         "description": "Saturn in own sign Capricorn in 7th house"},
    ],
    "divisional_charts": {
        "d2": {
            "lagna": "Leo", "lagna_lord": "Sun",
            "sun_hora_planets": ["Sun", "Mars", "Jupiter", "Saturn", "Rahu"],
            "moon_hora_planets": ["Moon", "Mercury", "Venus", "Ketu"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Virgo", "planets": {}},
        "d9": {
            "lagna": "Scorpio",
            "planets": {
                "Jupiter": {"sign_index": 3, "house": 9},
                "Saturn": {"sign_index": 9, "house": 3},
            },
        },
        "d10": {
            "lagna": "Pisces",
            "planets": {
                "Jupiter": {"sign_index": 11, "sign": "Pisces", "house": 1},
                "Saturn": {"sign_index": 9, "sign": "Capricorn", "house": 11},
            },
        },
        "d60": {"planet_analysis": {}},
    },
    "archetype": {"name": "The Advisor"},
}


# ─── RAMAN: Capricorn rising — regression check
RAMAN_CHART = {
    "lagna": {"sign_index": 9, "sign": "Capricorn", "longitude": 280.0, "degree": 10.0},
    "planets": {
        "Sun": {
            "sign_index": 7, "sign": "Scorpio", "house": 11,
            "degree": 15.0, "longitude": 225.0,
            "nakshatra": "Anuradha", "nakshatra_lord": "Saturn",
        },
        "Moon": {
            "sign_index": 11, "sign": "Pisces", "house": 3,
            "degree": 28.0, "longitude": 358.0,
            "nakshatra": "Revati", "nakshatra_lord": "Mercury",
        },
        "Mars": {
            "sign_index": 6, "sign": "Libra", "house": 10,
            "degree": 20.0, "longitude": 200.0,
            "nakshatra": "Swati", "nakshatra_lord": "Rahu",
        },
        "Mercury": {
            "sign_index": 6, "sign": "Libra", "house": 10,
            "degree": 5.0, "longitude": 185.0,
            "nakshatra": "Chitra", "nakshatra_lord": "Mars",
        },
        "Jupiter": {
            "sign_index": 10, "sign": "Aquarius", "house": 2,
            "degree": 12.0, "longitude": 312.0,
            "nakshatra": "Shatabhisha", "nakshatra_lord": "Rahu",
        },
        "Venus": {
            "sign_index": 7, "sign": "Scorpio", "house": 11,
            "degree": 10.0, "longitude": 220.0,
            "nakshatra": "Anuradha", "nakshatra_lord": "Saturn",
        },
        "Saturn": {
            "sign_index": 2, "sign": "Gemini", "house": 6,
            "degree": 18.0, "longitude": 78.0,
            "nakshatra": "Ardra", "nakshatra_lord": "Rahu",
        },
        "Rahu": {
            "sign_index": 7, "sign": "Scorpio", "house": 11,
            "degree": 22.0, "longitude": 232.0,
            "nakshatra": "Jyeshtha", "nakshatra_lord": "Mercury",
        },
        "Ketu": {
            "sign_index": 1, "sign": "Taurus", "house": 5,
            "degree": 22.0, "longitude": 52.0,
            "nakshatra": "Rohini", "nakshatra_lord": "Moon",
        },
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {
            "lagna": "Cancer", "lagna_lord": "Moon",
            "sun_hora_planets": ["Mars", "Saturn"],
            "moon_hora_planets": ["Sun", "Moon", "Mercury", "Jupiter", "Venus", "Rahu"],
            "wealth_signals": [],
        },
        "d4": {
            "planets": {
                "Jupiter": {"sign_index": 3, "house": 7},
                "Venus": {"sign_index": 0, "house": 4},
                "Mars": {"sign_index": 9, "house": 1},
                "Saturn": {"sign_index": 6, "house": 10},
            },
        },
        "d7": {"lagna": "Aries", "planets": {}},
        "d9": {"lagna": "Cancer", "planets": {}},
        "d10": {
            "lagna": "Scorpio",
            "planets": {
                "Mercury": {"sign_index": 6, "sign": "Libra", "house": 10},
                "Jupiter": {"sign_index": 10, "sign": "Aquarius", "house": 4},
                "Venus": {"sign_index": 7, "sign": "Scorpio", "house": 1},
                "Mars": {"sign_index": 0, "sign": "Aries", "house": 6},
                "Saturn": {"sign_index": 2, "sign": "Gemini", "house": 8},
            },
        },
        "d60": {
            "planet_analysis": {
                "Mercury": {"karma_name": "Bhrashta", "karma_desc": "fallen karma", "is_positive": False, "is_challenging": True},
            },
        },
    },
    "archetype": {"name": "The Broker"},
}


# ─── MOON PRESSURE CHART: Moon in H2 during Moon MD, Jyeshtha nakshatra
MOON_PRESSURE_CHART = {
    "lagna": {"sign_index": 6, "sign": "Libra", "longitude": 180.0, "degree": 10.0},
    "planets": {
        "Sun": {
            "sign_index": 8, "sign": "Sagittarius", "house": 3,
            "degree": 15.0, "longitude": 255.0,
            "nakshatra": "Purva Ashadha", "nakshatra_lord": "Venus",
        },
        "Moon": {
            "sign_index": 7, "sign": "Scorpio", "house": 2,
            "degree": 22.0, "longitude": 232.0,
            "nakshatra": "Jyeshtha", "nakshatra_lord": "Mercury",
        },
        "Mars": {
            "sign_index": 0, "sign": "Aries", "house": 7,
            "degree": 10.0, "longitude": 10.0,
            "nakshatra": "Ashvini", "nakshatra_lord": "Ketu",
        },
        "Mercury": {
            "sign_index": 8, "sign": "Sagittarius", "house": 3,
            "degree": 5.0, "longitude": 245.0,
            "nakshatra": "Mula", "nakshatra_lord": "Ketu",
        },
        "Jupiter": {
            "sign_index": 11, "sign": "Pisces", "house": 6,
            "degree": 20.0, "longitude": 350.0,
            "nakshatra": "Revati", "nakshatra_lord": "Mercury",
        },
        "Venus": {
            "sign_index": 7, "sign": "Scorpio", "house": 2,
            "degree": 8.0, "longitude": 218.0,
            "nakshatra": "Anuradha", "nakshatra_lord": "Saturn",
        },
        "Saturn": {
            "sign_index": 9, "sign": "Capricorn", "house": 4,
            "degree": 12.0, "longitude": 282.0,
            "nakshatra": "Shravana", "nakshatra_lord": "Moon",
        },
        "Rahu": {
            "sign_index": 3, "sign": "Cancer", "house": 10,
            "degree": 15.0, "longitude": 105.0,
            "nakshatra": "Pushya", "nakshatra_lord": "Saturn",
        },
        "Ketu": {
            "sign_index": 9, "sign": "Capricorn", "house": 4,
            "degree": 15.0, "longitude": 285.0,
            "nakshatra": "Shravana", "nakshatra_lord": "Moon",
        },
    },
    "yogas": [],
    "divisional_charts": {
        "d2": {
            "lagna": "Libra", "lagna_lord": "Venus",
            "sun_hora_planets": ["Sun", "Mars"],
            "moon_hora_planets": ["Moon", "Mercury", "Jupiter", "Venus", "Saturn"],
            "wealth_signals": [],
        },
        "d4": {"planets": {}},
        "d7": {"lagna": "Aries", "planets": {}},
        "d9": {"lagna": "Cancer", "planets": {}},
        "d10": {"lagna": "Scorpio", "planets": {}},
        "d60": {"planet_analysis": {}},
    },
    "current_dasha": {"md_lord": "Moon"},
    "archetype": {"name": "The Broker"},
}


# ═══════════════════════════════════════════════════════════════════════════
# TEST FUNCTIONS
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


# ─── TEST GROUP 1: VIPARITA STACK DETECTION ─────────────────────────────────
print("\n═══ TEST GROUP 1: Viparita Stack Detection ═══")

# Test 1: Musk should have triple viparita (from pre-computed yogas)
musk_vip = detect_viparita_stack(MUSK_CHART)
run_test(
    "Musk: triple viparita detected",
    musk_vip.get("tier") == "extreme" and musk_vip.get("count") >= 3,
    f"Got tier={musk_vip.get('tier')}, count={musk_vip.get('count')}",
)

# Test 2: Raman should have no viparita
raman_vip = detect_viparita_stack(RAMAN_CHART)
run_test(
    "Raman: no viparita",
    raman_vip.get("tier") == "none" or raman_vip.get("count", 0) == 0,
    f"Got tier={raman_vip.get('tier')}, count={raman_vip.get('count')}",
)

# Test 3: Viparita weight for extreme tier = 6.0
run_test(
    "Musk: viparita weight = 6.0",
    musk_vip.get("weight") == 6.0,
    f"Got weight={musk_vip.get('weight')}",
)


# ─── TEST GROUP 2: IDENTITY OVERWHELM DETECTION ────────────────────────────
print("\n═══ TEST GROUP 2: Identity Overwhelm Detection ═══")

# Test 4: Shashi should trigger identity overwhelm (4 planets in H1)
shashi_io = detect_identity_overwhelm(SHASHI_CHART)
run_test(
    "Shashi: identity overwhelm detected",
    shashi_io is not None and shashi_io.get("flag") == "identity_overwhelm",
    f"Got {shashi_io}",
)

# Test 5: Shashi H1 count should be >= 3
run_test(
    "Shashi: H1 count >= 3",
    shashi_io is not None and shashi_io.get("h1_count", 0) >= 3,
    f"Got h1_count={shashi_io.get('h1_count') if shashi_io else 'None'}",
)

# Test 6: Raman should NOT trigger identity overwhelm
raman_io = detect_identity_overwhelm(RAMAN_CHART)
run_test(
    "Raman: no identity overwhelm",
    raman_io is None,
    f"Got {raman_io}",
)

# Test 7: Andres should NOT trigger (Jupiter+Moon in H1 = 2, not 3)
andres_io = detect_identity_overwhelm(ANDRES_CHART)
run_test(
    "Andres: no identity overwhelm (only 2 in H1)",
    andres_io is None,
    f"Got {andres_io}",
)


# ─── TEST GROUP 3: MOON MD H2 PRESSURE ─────────────────────────────────────
print("\n═══ TEST GROUP 3: Moon MD H2 Pressure ═══")

# Test 8: Moon pressure chart with Moon MD should trigger
moon_p = check_moon_md_h2_pressure(MOON_PRESSURE_CHART, "Moon")
run_test(
    "Moon pressure chart: triggers during Moon MD",
    moon_p is not None and moon_p.get("flag") == "moon_md_h2_pressure",
    f"Got {moon_p}",
)

# Test 9: Moon pressure should be high severity (Jyeshtha is intense)
run_test(
    "Moon pressure: high severity (Jyeshtha nakshatra)",
    moon_p is not None and moon_p.get("severity") == "high",
    f"Got severity={moon_p.get('severity') if moon_p else 'None'}",
)

# Test 10: Same chart without Moon MD should NOT trigger
moon_p_no_md = check_moon_md_h2_pressure(MOON_PRESSURE_CHART, "Saturn")
run_test(
    "Moon pressure: no trigger during Saturn MD",
    moon_p_no_md is None,
    f"Got {moon_p_no_md}",
)


# ─── TEST GROUP 4: D-2 HORA BUSINESS MISMATCH ──────────────────────────────
print("\n═══ TEST GROUP 4: D-2 Hora Business Mismatch ═══")

# Test 11: Raman has strong moon hora (6 planets) — PHYSICAL_OPS (sun) should mismatch
raman_hora = check_d2_hora_business_mismatch(RAMAN_CHART, "PHYSICAL_OPS")
run_test(
    "Raman: PHYSICAL_OPS mismatches moon-hora dominance",
    raman_hora is not None and raman_hora.get("flag") == "hora_business_mismatch",
    f"Got {raman_hora}",
)

# Test 12: Raman with ADVISORY (moon) should NOT mismatch
raman_hora_adv = check_d2_hora_business_mismatch(RAMAN_CHART, "ADVISORY")
run_test(
    "Raman: ADVISORY matches moon-hora (no mismatch)",
    raman_hora_adv is None,
    f"Got {raman_hora_adv}",
)

# Test 13: Andres has 5 sun hora vs 4 moon hora — difference < 2 = balanced (no mismatch)
andres_hora = check_d2_hora_business_mismatch(ANDRES_CHART, "ADVISORY")
run_test(
    "Andres: balanced hora (5 vs 4) — no mismatch for ADVISORY",
    andres_hora is None,
    f"Got {andres_hora}",
)


# ─── TEST GROUP 5: ARCHETYPE CLASSIFICATION ────────────────────────────────
print("\n═══ TEST GROUP 5: Archetype Classification ═══")

# Test 14: Musk should classify as DISRUPTOR
musk_arch = classify_wealth_archetype(
    MUSK_CHART,
    viparita_result=musk_vip,
)
run_test(
    "Musk: DISRUPTOR archetype",
    musk_arch.get("primary_archetype") == "DISRUPTOR",
    f"Got {musk_arch.get('primary_archetype')} (score={musk_arch.get('primary_score')})",
)

# Test 15: Musk DISRUPTOR score should be >= 6.0
run_test(
    "Musk: DISRUPTOR score >= 6.0",
    musk_arch.get("primary_score", 0) >= 6.0,
    f"Got {musk_arch.get('primary_score')}",
)

# Test 16: Shashi should classify as CHARISMA
shashi_arch = classify_wealth_archetype(
    SHASHI_CHART,
    identity_overwhelm=shashi_io,
)
run_test(
    "Shashi: CHARISMA archetype",
    shashi_arch.get("primary_archetype") == "CHARISMA",
    f"Got {shashi_arch.get('primary_archetype')} (scores: {json.dumps({k: v['score'] for k, v in shashi_arch.get('all_scores', {}).items()})})",
)

# Test 17: Mass server chart should classify as MASS_SERVER
ms_arch = classify_wealth_archetype(MASS_SERVER_CHART)
run_test(
    "Mass server: MASS_SERVER archetype",
    ms_arch.get("primary_archetype") == "MASS_SERVER",
    f"Got {ms_arch.get('primary_archetype')} (scores: {json.dumps({k: v['score'] for k, v in ms_arch.get('all_scores', {}).items()})})",
)

# Test 18: Andres should classify as INSTITUTIONAL or SYSTEMATIC
andres_mp = detect_mahapurusha_stack(ANDRES_CHART)
andres_yk = detect_yogakaraka_activation(ANDRES_CHART)
andres_arch = classify_wealth_archetype(
    ANDRES_CHART,
    mahapurusha_result=andres_mp,
    yogakaraka_result=andres_yk,
)
run_test(
    "Andres: INSTITUTIONAL or SYSTEMATIC archetype",
    andres_arch.get("primary_archetype") in ("INSTITUTIONAL", "SYSTEMATIC"),
    f"Got {andres_arch.get('primary_archetype')} (scores: {json.dumps({k: v['score'] for k, v in andres_arch.get('all_scores', {}).items()})})",
)


# ─── TEST GROUP 6: ARCHETYPE OUTPUT STRUCTURE ──────────────────────────────
print("\n═══ TEST GROUP 6: Archetype Output Structure ═══")

# Test 19: Archetype result has all required keys
required_keys = [
    "primary_archetype", "primary_score", "primary_label",
    "primary_description", "primary_reasons", "all_scores",
    "favored_vehicles", "disfavored_vehicles", "honest_read",
]
missing = [k for k in required_keys if k not in musk_arch]
run_test(
    "Archetype result has all required keys",
    len(missing) == 0,
    f"Missing: {missing}",
)

# Test 20: honest_read is a non-empty string
run_test(
    "honest_read is non-empty string",
    isinstance(musk_arch.get("honest_read"), str) and len(musk_arch.get("honest_read", "")) > 20,
    f"Got: {repr(musk_arch.get('honest_read', '')[:50])}",
)

# Test 21: all_scores contains all 5 archetypes
all_arch = set(musk_arch.get("all_scores", {}).keys())
expected_arch = {"DISRUPTOR", "SYSTEMATIC", "MASS_SERVER", "CHARISMA", "INSTITUTIONAL"}
run_test(
    "all_scores has all 5 archetypes",
    all_arch == expected_arch,
    f"Got: {all_arch}",
)


# ─── TEST GROUP 7: V4 INTEGRATION INTO BUSINESS_FIT ────────────────────────
print("\n═══ TEST GROUP 7: v4 Integration in business_fit.py ═══")

# Test 22: analyze_business_fit returns v4 keys
musk_bf = analyze_business_fit(MUSK_CHART)
v4_keys = ["wealth_archetype", "viparita_stack", "critical_warnings", "honest_scale_read"]
missing_v4 = [k for k in v4_keys if k not in musk_bf]
run_test(
    "business_fit returns v4 keys",
    len(missing_v4) == 0,
    f"Missing: {missing_v4}",
)

# Test 23: signature_version is 4.0
run_test(
    "signature_version is 4.0",
    musk_bf.get("signature_version") == "4.0",
    f"Got: {musk_bf.get('signature_version')}",
)

# Test 24: wealth_archetype has primary_archetype
wa = musk_bf.get("wealth_archetype", {})
run_test(
    "wealth_archetype.primary_archetype exists",
    wa.get("primary_archetype") in expected_arch,
    f"Got: {wa.get('primary_archetype')}",
)

# Test 25: honest_scale_read is non-empty
run_test(
    "honest_scale_read is non-empty",
    isinstance(musk_bf.get("honest_scale_read"), str) and len(musk_bf.get("honest_scale_read", "")) > 10,
    f"Got: {repr(musk_bf.get('honest_scale_read', '')[:50])}",
)

# Test 26: Raman v4 integration regression — still returns favored categories
raman_bf = analyze_business_fit(RAMAN_CHART)
run_test(
    "Raman: still returns favored_categories (v4 regression)",
    isinstance(raman_bf.get("favored_categories"), list),
    f"Got type: {type(raman_bf.get('favored_categories'))}",
)

# Test 27: Raman still has modern_corrections (v3 regression)
run_test(
    "Raman: still returns modern_corrections (v3 regression)",
    isinstance(raman_bf.get("modern_corrections"), dict),
    f"Got type: {type(raman_bf.get('modern_corrections'))}",
)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  v4 ARCHETYPE TESTS: {passed}/{total} passed, {failed} failed")
print(f"{'═' * 60}")

if failed > 0:
    print("\n⚠️  Some tests failed. Review output above.")
    sys.exit(1)
else:
    print("\n✅ All v4 tests passed!")
    sys.exit(0)
