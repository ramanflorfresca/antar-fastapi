"""
tests/hora_rules_prespecified.py
Six D-2 WEALTH rules, FIXED before the confirmatory cohort exists.   2026-07-23

Committed and pushed BEFORE the product owner sends charts. This repository has
now recorded twenty-three dead hypotheses, and at least two of them died because
they were invented after looking at a chart that flattered them. The defence is
a timestamp.

────────────────────────────────────────────────────────────────────────────
WHERE THE HYPOTHESIS CAME FROM, AND WHY THOSE CHARTS MUST NOW BE THROWN AWAY
────────────────────────────────────────────────────────────────────────────
A pilot on three billionaires with usable birth times:

    Bill Gates      7 grahas in the Sun's hora
    Elon Musk       6          (birth time UNVERIFIED)
    Mukesh Ambani   5
    -------------------------------------------------
    mean 6.00   vs cohort (n=93) mean 4.27, sd 1.47   permutation p = 0.038

Those three GENERATED this hypothesis, so they cannot also test it. Including
them would be scoring the same coin flip twice. They are excluded from the
confirmatory analysis by name. If the effect is real it will appear in charts
that had no hand in proposing it.

The direction is pre-specified and therefore tested ONE-TAILED: the wealthy are
predicted to have MORE grahas in the Sun's hora. This is the opposite of the
product owner's own intuition — he expected the Moon's hora (wealth that comes
easily) to mark the wealthy. Writing the direction down now means the result can
embarrass either of us, which is the point.

────────────────────────────────────────────────────────────────────────────
PROTOCOL, FIXED IN ADVANCE
────────────────────────────────────────────────────────────────────────────
GROUPING. Assigned from the owner's own description of each person BEFORE any
chart is computed. Three groups:
    A  real wealth built     — sold a company, holds substantial assets, or
                               runs a business at material scale
    B  professionally successful, ordinary means
    C  neither
The owner assigns. I do not, and I do not revise an assignment after seeing a
score.

BIRTH TIME. Every chart carries a reliability tag before scoring:
    A  documented (birth certificate, hospital record, family record)
    B  stated by the person from memory
    C  third-party or widely-cited but unverified
    X  unknown — EXCLUDED entirely, not analysed
Rules H1-H5 use whole-chart or lagna-based quantities and tolerate tag C. Rule
H6 depends on Sri Lagna, which moves ~30 degrees per HOUR — a whole sign —
because it compounds the ascendant's motion with the Moon's nakshatra traverse.
H6 IS THEREFORE RESTRICTED TO TAG A AND B CHARTS, decided here and not later.

AGE. Born 1990 or earlier. Wealth needs time to become a fact, exactly as
"not famous" did in the fame work.

STATISTICS. Monte-Carlo permutation, 200,000 draws, one-tailed in the
pre-specified direction. Six tests, so the Bonferroni threshold is
p < 0.05/6 = 0.0083. A rule at p = 0.04 has NOT survived and will not be
described as promising.

REPORTING. Every rule reported, including and especially the failures. No rule
added, removed, reworded or re-thresholded once the data arrives. If I want a
seventh idea after seeing the charts, it goes in a new pre-registration and
waits for a new cohort.

MINIMUM N. Below 12 charts in group A this is not run at all — it is written up
as underpowered. n=3 taught me what that costs.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine.hora_chart import (          # noqa: E402
    hora_positions, hora_split, house_lord_in_hora, nature_match,
    SUN_HORA, MOON_HORA,
)

# Charts that produced the hypothesis. Excluded from the confirmatory test.
PILOT_EXCLUDED = {"Bill Gates", "Elon Musk", "Mukesh Ambani"}

MIN_GROUP_A = 12
BONFERRONI = 0.05 / 6


# ── H1 — the split. The headline rule, and the only one with a pilot ────────
# PREDICTION: group A has a HIGHER count of grahas in the Sun's hora.
def h1_sun_hora_count(cd):
    s = hora_split(cd)
    return float(s["sun_hora"]) if s.get("available") else None


# ── H2 — the 2nd lord, the money you hold, in the Sun's hora ────────────────
# Rao's school's method: the D-1 house lord read in the corresponding varga.
# PREDICTION: group A more often has the 2nd lord in the Sun's hora.
def h2_second_lord_sun_hora(cd):
    r = house_lord_in_hora(cd, 2)
    return float(r["hora"] == SUN_HORA) if r.get("available") else None


# ── H3 — the 11th lord, the money that comes in, in the Sun's hora ──────────
# PREDICTION: group A more often has the 11th lord in the Sun's hora.
def h3_eleventh_lord_sun_hora(cd):
    r = house_lord_in_hora(cd, 11)
    return float(r["hora"] == SUN_HORA) if r.get("available") else None


# ── H4 — the ascendant itself in the Sun's hora ─────────────────────────────
# The person's own orientation, as distinct from how their money behaves.
# PREDICTION: group A more often has the lagna in the Sun's hora.
def h4_lagna_sun_hora(cd):
    h = hora_positions(cd).get("Lagna")
    return float(h == SUN_HORA) if h else None


# ── H5 — nature match on the 2nd lord ───────────────────────────────────────
# The only dignity D-2 supports: malefic in the Sun's hora, benefic in the
# Moon's. Fires for 56% of the base, so it is expected to be weak. It is
# included precisely BECAUSE it is the rule currently shipping in the product —
# if it does not separate, the product line built on it has to soften.
# PREDICTION: group A more often has the 2nd lord nature-matched.
def h5_second_lord_nature_match(cd):
    r = house_lord_in_hora(cd, 2)
    if not r.get("available"):
        return None
    m = nature_match(cd, r["lord"])
    return None if m is None else float(m)


# ── H6 — the Sri Lagna's lord in the Sun's hora ─────────────────────────────
# TAG A AND B BIRTH TIMES ONLY — see PROTOCOL. Sri Lagna moves a full sign per
# hour, so a tag-C time makes this rule meaningless rather than merely noisy.
# The nakshatra-lord variant of this chain is ALREADY DEAD (1/11 against 2.8
# expected, p=0.962, tests/negative_result_d2_wealth_chain.md) and is not
# resurrected here. This tests the SIGN lord's hora, which was never tested.
# PREDICTION: group A more often has the Sri Lagna lord in the Sun's hora.
def h6_sri_lagna_lord_sun_hora(cd):
    from antar_engine.sri_lagna import sri_lagna
    sl = sri_lagna(cd)
    if not sl.get("available"):
        return None
    lon = ((cd.get("planets") or {}).get(sl["lord"]) or {}).get("longitude")
    from antar_engine.hora_chart import _hora_of
    h = _hora_of(lon)
    return float(h == SUN_HORA) if h else None


RULES = [
    ("H1 grahas in the Sun's hora",        h1_sun_hora_count,        "ABC"),
    ("H2 2nd lord in the Sun's hora",      h2_second_lord_sun_hora,  "ABC"),
    ("H3 11th lord in the Sun's hora",     h3_eleventh_lord_sun_hora, "ABC"),
    ("H4 lagna in the Sun's hora",         h4_lagna_sun_hora,        "ABC"),
    ("H5 2nd lord nature-matched",         h5_second_lord_nature_match, "ABC"),
    ("H6 Sri Lagna lord in the Sun's hora", h6_sri_lagna_lord_sun_hora, "AB"),
]
# third field = birth-time reliability tags this rule may use.

DIRECTION = "group A scores HIGHER on every rule above"
