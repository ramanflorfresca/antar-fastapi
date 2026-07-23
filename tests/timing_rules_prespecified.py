"""
tests/timing_rules_prespecified.py
Achievement as TIMING, not strength. Fixed 2026-07-23 before scoring.

Seventeen natal-strength hypotheses have failed in this repository — ten for
fame, seven for success — with the direction consistently backwards. This tests
a different mechanism, and one that has survived everywhere else here: not how
strong a chart is, but WHEN its wealth-giving periods fall.

The reasoning. Two people can carry identical wealth promise and live completely
different lives, because one receives his wealth mahadasha at 25 and the other
at 70. Same yogas, different birth minute, different dasha start. Nearly every
chart contains some wealth-giver; what differs is whether its period lands
inside the years a person can actually build.

That also matches the only findings that have survived scrutiny here — Shashi's
three dated transitions each on the classically correct antardasha lord, the
Upapada marriage rule, the blind career-mode test. Every one is about WHICH KIND
and WHEN. None is about HOW MUCH.

    T1  productive wealth-years: years of a wealth-lord MAHADASHA falling
        between ages 25 and 65
    T2  the single longest such uninterrupted window
    T3  age at which the first productive wealth mahadasha begins
        (lower is better — more runway)
    T4  fraction of ages 25-65 spent inside a wealth mahadasha

A wealth-giver is the lord of the 2nd, 11th or 9th, or any planet sitting in the
2nd or 11th.

PROTOCOL, fixed in advance: same groups and same charts as the success test —
8 who built or earned substantially, 19 ordinary, all born 1990 or earlier.
200,000 sampled permutations per rule, seed 20260723. Bonferroni threshold for
four tests: p < 0.0125. Every rule reported, including failures. Nothing added
or adjusted once the numbers are seen.
"""
import datetime

SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
LOW, HIGH = 25, 65          # the years a person can actually build


def wealth_givers(cd):
    li = cd["lagna"]["sign_index"]
    lord = lambda h: SIGN_LORD[(li + h - 1) % 12]
    g = {lord(h) for h in (2, 11, 9)}
    for p, d in (cd.get("planets") or {}).items():
        if isinstance(d, dict) and d.get("house") in (2, 11):
            g.add(p)
    return g


def _windows(cd, dashas, birth):
    """[(age_start, age_end)] of wealth mahadashas clipped to productive years."""
    g = wealth_givers(cd)
    out = []
    for r in (dashas.get("vimsottari") or []):
        if not isinstance(r, dict) or str(r.get("level")) != "mahadasha":
            continue
        if (r.get("lord_or_sign") or r.get("planet_or_sign")) not in g:
            continue
        try:
            s = datetime.date.fromisoformat(str(r.get("start_date"))[:10])
            e = datetime.date.fromisoformat(str(r.get("end_date"))[:10])
        except Exception:
            continue
        a0 = (s - birth).days / 365.25
        a1 = (e - birth).days / 365.25
        lo, hi = max(a0, LOW), min(a1, HIGH)
        if hi > lo:
            out.append((lo, hi))
    return sorted(out)


def t1_productive_years(cd, dashas, birth):
    return round(sum(b - a for a, b in _windows(cd, dashas, birth)), 2)


def t2_longest_window(cd, dashas, birth):
    w = _windows(cd, dashas, birth)
    return round(max((b - a for a, b in w), default=0.0), 2)


def t3_first_start_age(cd, dashas, birth):
    w = _windows(cd, dashas, birth)
    return round(w[0][0], 2) if w else float(HIGH)


def t4_fraction(cd, dashas, birth):
    return round(t1_productive_years(cd, dashas, birth) / (HIGH - LOW), 3)


# T3 is inverted at scoring time: an earlier start is better, so the test
# compares -T3. Recorded here so the direction is fixed in advance.
RULES = [
    ("T1 productive wealth-years (25-65)", t1_productive_years, False),
    ("T2 longest single window", t2_longest_window, False),
    ("T3 age first window opens (lower better)", t3_first_start_age, True),
    ("T4 fraction of 25-65 in a wealth period", t4_fraction, False),
]
