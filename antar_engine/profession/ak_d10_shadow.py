"""
antar_engine/profession/ak_d10_shadow.py — Atmakaraka x D-10 SHADOW experiment.

NOT WIRED to any endpoint. Pure functions + a frozen pre-registration; the
runner is tests/ak_d10_shadow_run.py. Nothing here may be imported by a surface
until the experiment passes AND the owner approves (same doctrine as
profession/README.md).

QUESTION
  Does the Atmakaraka (AK) — and where the AK sits in the D-10 — carry any
  information about WHAT KIND OF WORK a person does, beyond the AK planet alone?

  The AK->work table is the one proposed in the external "Wealth x Work x
  Karma-Dharma" framework (Sun=authority/medicine/government, Mars=sport/
  military, Mercury=writing, Venus=arts, ...). It is a classical-sounding table,
  not a tested one. This module freezes it BEFORE any outcome is looked at.

WHY LAGNA-FREE
  The OGDB birth times are rounded (French times to the hour until the 1920s).
  The D-10 lagna changes every ~12 minutes, so any D-10 *house* feature would be
  noise. Planet D-10 *signs* barely depend on clock time, so every feature here
  uses planet longitudes only.

PRE-REGISTRATION (frozen — change = new experiment, new file)
  Groups (OGDB OCCU slugs -> AK karaka set K(G)):
    SPORT_MIL  K={Mars}     Sun/Mars table row: sports, military
    ARTS       K={Venus}    painter, musician, actor, artist
    WORDS      K={Mercury}  writer, novelist, poet, journalist
    SUN_CLASS  K={Sun}      politician, physician, executive
  Baseline (context, NOT in the family):
    T0[G]  P(in G | AK in K(G))  vs  P(in G | AK not in K(G))
  Primary family (8 tests, Bonferroni p < 0.05/8 = 0.00625, one-sided, higher):
    T1[G]  within AK in K(G): P(in G | AK exalted/own in D-10) vs not
    T2[G]  whole cohort:      P(in G | D-10 dispositor of AK in K(G)) vs not
  Interpretation gate: if T0 fails for every group the AK->work table is itself
  dead and T1/T2 cannot rescue it.
"""
from __future__ import annotations

import hashlib
import json
from math import lgamma, exp, log

from ..d_charts_calculator import (
    SIGNS, SIGN_LORDS, _divisional_sign_index, _planet_strength,
)

KARAKA_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

# ── FROZEN PRE-REGISTRATION ─────────────────────────────────────────────────
GROUPS = {
    "SPORT_MIL": {
        "karaka": ["Mars"],
        "slugs": ["football-player", "cyclist", "athletics-competitor", "boxer",
                  "american-football-player", "basketball-player",
                  "rugby-union-player", "rugby-player", "rugby-league-player",
                  "tennis-player", "motor-sports-competitor", "swimmer", "skier",
                  "fencer", "golfer", "rower", "baseball-player",
                  "field-hockey-player", "gymnast", "weightlifter", "wrestler",
                  "sportsperson", "basque-pelota-player", "equestrian",
                  "sport-shooter", "military-personnel", "aircraft-pilot"],
    },
    "ARTS": {"karaka": ["Venus"],
             "slugs": ["painter", "musician", "actor", "artist"]},
    "WORDS": {"karaka": ["Mercury"],
              "slugs": ["writer", "novelist", "poet", "journalist",
                        "fictional-writer"]},
    "SUN_CLASS": {"karaka": ["Sun"],
                  "slugs": ["politician", "physician", "executive"]},
}
ALPHA_FAMILY = 0.05
N_PRIMARY = 8
BONFERRONI = ALPHA_FAMILY / N_PRIMARY


def prereg_hash() -> str:
    """Stable hash of the frozen design; printed in every result file."""
    blob = json.dumps({"groups": GROUPS, "n_primary": N_PRIMARY,
                       "alpha": ALPHA_FAMILY}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ── Features (pure; longitudes are SIDEREAL, 0-360) ─────────────────────────
def atmakaraka(longitudes: dict) -> str:
    """AK = the classical planet with the highest degree WITHIN its sign.

    NOTE: karakas.get_all_karakas() sorts by ABSOLUTE longitude (0-360), which
    picks the planet furthest round the zodiac, not the one with the highest
    in-sign degree. This function is the correct rule; see the runner's
    diagnostic for how often the two disagree.
    """
    return max(KARAKA_PLANETS, key=lambda p: (longitudes[p] % 30.0,
                                              -KARAKA_PLANETS.index(p)))


def atmakaraka_absolute_longitude(longitudes: dict) -> str:
    """The karakas.py behaviour (sort by absolute longitude) — diagnostic only."""
    return max(KARAKA_PLANETS, key=lambda p: longitudes[p])


def ak_d10_features(longitudes: dict) -> dict:
    ak = atmakaraka(longitudes)
    d10_idx = _divisional_sign_index(longitudes[ak], 10)
    d10_sign = SIGNS[d10_idx]
    return {
        "ak": ak,
        "ak_d10_sign": d10_sign,
        "ak_d10_dignified": _planet_strength(ak, d10_sign) in ("exalted", "own"),
        "ak_d10_dispositor": SIGN_LORDS[d10_sign],
    }


def groups_for_slugs(occu: str) -> set:
    slugs = set(occu.split("+"))
    return {g for g, spec in GROUPS.items() if slugs & set(spec["slugs"])}


# ── Exact one-sided Fisher (higher-in-first-row), no scipy ──────────────────
def _log_comb(n, k):
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def fisher_one_sided(a, b, c, d) -> float:
    """2x2 [[a,b],[c,d]]: row1 = feature present (a in group, b not),
    row2 = feature absent. P(X >= a) under the hypergeometric null."""
    n1, n2, k = a + b, c + d, a + c
    n = n1 + n2
    if n1 == 0 or n2 == 0 or k == 0:
        return 1.0
    lo, hi = max(0, k - n2), min(k, n1)
    denom = _log_comb(n, k)
    return min(1.0, sum(exp(_log_comb(n1, x) + _log_comb(n2, k - x) - denom)
                        for x in range(a, hi + 1) if lo <= x <= hi))


def lift(a, b, c, d):
    r1 = a / (a + b) if (a + b) else float("nan")
    r2 = c / (c + d) if (c + d) else float("nan")
    return r1, r2, (r1 / r2 if r2 else float("nan"))
