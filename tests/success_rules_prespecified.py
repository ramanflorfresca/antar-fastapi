"""
tests/success_rules_prespecified.py
Seven classical WEALTH / SUCCESS indicators, FIXED before the cohort exists.

Committed and pushed BEFORE the product owner sends a single chart. Ten fame
hypotheses have already died in this repository, one of them because it was
invented after looking at a chart that flattered it. The defence is a timestamp.

WHY SUCCESS RATHER THAN FAME. The fame question is dead — six classical rules
across three groups, best p = 0.489 against a threshold of 0.0083, with the
famous scoring LOWER than the ordinary on four of six. But fame is also not what
users ask about. Nobody opens this app wondering whether they will be famous.
They open it wondering whether the work will pay off. That question has a much
larger natural cohort and is worth answering properly.

WHAT IS DIFFERENT THIS TIME, and it is a criticism of the last attempt:

  The fame rules were implemented in their simplest form and that weakened them.
  Raja yoga forms three ways — conjunction, exchange (parivartana), and mutual
  aspect — and only conjunction was coded. Sun's digbala is specifically the
  10th house and was widened to 9/10/11, diluting it. Here the yoga detection
  handles all three forms, and Vedic aspects are implemented properly: every
  planet aspects the 7th from itself, Mars additionally the 4th and 8th,
  Jupiter the 5th and 9th, Saturn the 3rd and 10th.

  Dignity is taken from planet_significations.contextual_strength rather than
  sign-dignity alone. That function exists because dignity-only scoring read
  "Rahu in the 11th with Sun and Venus" as nothing, and it is already the basis
  of the vocational work in this codebase.

SCORING PROTOCOL, fixed in advance:
  - three groups, assigned from the owner's own descriptions before scoring
  - born 1990 or earlier: success needs time to become a fact, exactly as
    "not famous" does
  - exact permutation test per rule
  - Bonferroni threshold for seven tests: p < 0.0071
  - every rule reported, including and especially the failures
  - no rule added, removed or adjusted once the data arrives
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
EXALT = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
         "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
         "Saturn": "Libra"}
OWN = {"Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
       "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
       "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"]}
BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
KENDRA = {1, 4, 7, 10}
# The wealth-giving houses in Parashari: dhana (2), purva punya (5),
# bhagya (9), labha (11).
DHANA_HOUSES = (2, 5, 9, 11)


def _li(cd):
    return cd["lagna"]["sign_index"]


def _lord(cd, h):
    return SIGN_LORD[(_li(cd) + h - 1) % 12]


def _house(cd, p):
    return (cd["planets"].get(p) or {}).get("house")


def _sign(cd, p):
    return (cd["planets"].get(p) or {}).get("sign")


def _strength(cd, p):
    try:
        from antar_engine.planet_significations import contextual_strength
        return float((contextual_strength(p, cd) or {}).get("points") or 0.0)
    except Exception:
        return 0.0


def _aspects(cd, a, b):
    """Does planet a cast a Vedic aspect on planet b?

    Every planet aspects the 7th from itself. Mars adds the 4th and 8th,
    Jupiter the 5th and 9th, Saturn the 3rd and 10th. The fame attempt ignored
    this entirely and only counted conjunction, which is why its yoga counts
    were too low to mean anything.
    """
    ha, hb = _house(cd, a), _house(cd, b)
    if not (isinstance(ha, int) and isinstance(hb, int)):
        return False
    dist = ((hb - ha) % 12) + 1
    special = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10)}
    return dist == 7 or dist in special.get(a, ())


def _connected(cd, a, b):
    """Conjunction, exchange (parivartana), or mutual aspect — all three."""
    if a == b:
        return False
    ha, hb = _house(cd, a), _house(cd, b)
    if ha and hb and ha == hb:
        return True                                   # conjunction
    # exchange: each sits in a sign the other rules
    sa, sb = _sign(cd, a), _sign(cd, b)
    if sa in SIGNS and sb in SIGNS:
        if SIGN_LORD[SIGNS.index(sa)] == b and SIGN_LORD[SIGNS.index(sb)] == a:
            return True                               # parivartana
    return _aspects(cd, a, b) and _aspects(cd, b, a)  # mutual aspect


# ── S1 — Dhana yoga: the wealth-house lords connected to each other ──────
def s1_dhana_yoga(cd):
    lords = {h: _lord(cd, h) for h in DHANA_HOUSES}
    seen, n = set(), 0
    for h1, p1 in lords.items():
        for h2, p2 in lords.items():
            if h1 >= h2 or p1 == p2:
                continue
            key = tuple(sorted((p1, p2)))
            if key in seen:
                continue
            if _connected(cd, p1, p2):
                seen.add(key)
                n += 1
    return n


# ── S2..S5 — dignity of the lords that carry money and work ─────────────
def s2_second_lord(cd):
    return _strength(cd, _lord(cd, 2))


def s3_eleventh_lord(cd):
    return _strength(cd, _lord(cd, 11))


def s4_lagna_lord(cd):
    return _strength(cd, _lord(cd, 1))


def s5_tenth_lord(cd):
    return _strength(cd, _lord(cd, 10))


# ── S6 — vargottama count: planets holding the same sign in D-1 and D-9 ──
# The navamsa is the test of whether a promise is real. A planet keeping its
# sign in both delivers what the rasi offers.
def s6_vargottama(cd):
    d9 = ((cd.get("divisional_charts") or {}).get("d9") or {}).get("planets") or {}
    n = 0
    for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        a, b = _sign(cd, p), (d9.get(p) or {}).get("sign")
        if a and b and a == b:
            n += 1
    return n


# ── S7 — Lakshmi yoga: the 9th lord dignified in a kendra, lagna lord strong ──
def s7_lakshmi(cd):
    l9 = _lord(cd, 9)
    s9 = _sign(cd, l9)
    dignified = (s9 == EXALT.get(l9)) or (s9 in OWN.get(l9, []))
    in_kendra = _house(cd, l9) in KENDRA
    lagna_ok = _strength(cd, _lord(cd, 1)) >= 1.0
    return 1 if (dignified and in_kendra and lagna_ok) else 0


RULES = [
    ("S1 Dhana yoga (2/5/9/11 lords linked)", s1_dhana_yoga),
    ("S2 2nd lord dignity", s2_second_lord),
    ("S3 11th lord dignity", s3_eleventh_lord),
    ("S4 lagna lord dignity", s4_lagna_lord),
    ("S5 10th lord dignity", s5_tenth_lord),
    ("S6 vargottama count (D1=D9)", s6_vargottama),
    ("S7 Lakshmi yoga", s7_lakshmi),
]
