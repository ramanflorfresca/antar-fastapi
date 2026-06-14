"""
antar_engine/lk_rules/maturity.py — Lal Kitab planetary maturity (Graha Paripaka).

SOURCE: Lal Kitab — Goswami 1952 ed. / Mahajan 2014 rev. ed.

NOTE (deliberate divergence from Parashari):
  Mercury matures at 34 in the LK tradition. Classical Parashari Graha
  Paripaka uses 32. DO NOT substitute 32 here — this table is the LK value.

Semantics (LK): at the maturity age a planet's full potential manifests —
promise AND problem both become visible — and persists thereafter. For the
sleeping-planet gate the test is binary and INCLUSIVE: at exactly the maturity
age the planet IS mature. Below maturity, the planet's (annual) sleep is not
yet actionable and its awaken-remedy is suppressed.
"""

from __future__ import annotations

LK_MATURITY_AGE = {
    "Jupiter": 16,
    "Sun": 22,
    "Moon": 24,
    "Venus": 25,
    "Mars": 28,
    "Mercury": 34,   # LK value — NOT the Parashari 32
    "Saturn": 36,
    "Rahu": 42,
    "Ketu": 48,
}


def is_mature(planet: str, age: int) -> bool:
    """True if `planet` has reached LK maturity at `age` (inclusive).

    Unknown planet names raise KeyError on purpose — every one of the 9
    grahas must be in the table, and a typo should fail loudly rather than
    silently treat a planet as immature."""
    return age >= LK_MATURITY_AGE[planet]
