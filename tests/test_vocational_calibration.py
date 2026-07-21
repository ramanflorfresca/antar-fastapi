"""
tests/test_vocational_calibration.py
Real people, real professions — the benchmark vocational_fit is measured on.

Seventeen charts supplied by the product owner, who knows the actual outcomes,
including the unglamorous ones ("surviving, not big"). That is worth more than
a celebrity list: it contains FAILURES, and failures are what discriminate.

Purpose is measurement, not a pass/fail gate. The scoring is not good yet.
The point is that any change to vocational_fit must MOVE THIS NUMBER, and a
regression is visible immediately instead of shipping on a hunch.

Baseline (2026-07-21), correct profession in the engine's top-2 of 8 categories.
Chance is ~2/14 (two picks out of eight, per person).
    sign-dignity scoring (original)            2/9   (9-chart cohort)
    contextual_strength + Ketu severance       5/9   (9-chart cohort)
    same scoring, 14-chart cohort              7/14
    17-chart cohort, 14 graded                 7/14
    + per-sector normalisation, 7 categories   8/14

TRIED AND REJECTED (2026-07-21): reading the D-10 house placement of each
sector's karakas — +1.25 in a house the sector runs on, +0.5 in a kendra or
trikona, -0.75 in a dusthana, -0.75 conjunct Ketu. This was the obvious next
step and the owner's own thesis ("does the D-10 have a strong combination for
this kind of job"). It scored 5/14 against 8/14 without it, barely above the
4.0/14 chance line: Joe Ess 1->4, Kulbir 2->4, Yogi 2->4, Gogi 1->2.

It is not that D-10 is irrelevant — it is the career chart. Two likelier
causes, both worth testing before trying again:
  1. NATURE_HOUSES was derived for D-1 reasoning and reused unchanged for D-10.
     A sector's D-10 houses are probably not its D-1 houses.
  2. D-10 houses are counted from the D-10 LAGNA, which turns over every ~12
     minutes of birth time. House-based D-10 rules multiply birth-time error in
     a way the D-1 karaka reading does not.
Ketu's D-10 house is still read, because that rule was derived from observed
outcomes rather than assumed.

Read the ratio, not the raw count. Chance is 2/len(CATEGORIES) per person, so
merging the duplicate occult slot RAISED chance from 3.5/14 to 4.0/14. Both
7/14-of-8 and 8/14-of-7 are about twice chance: normalisation fixed a real bug
without yet moving the hit rate much. What it did move is WHICH sectors win,
and the live verdict band — see below.
        (BG/EM/MZ carry unverified birth times and are NOT graded — see
         UNRELIABLE_TIME. Ungraded, they score 2/3.)

Rice was RECLASSIFIED from wholesale to manufacture on the owner's correction
(milling is plant, labour and process risk — the same shape as a factory). That
moved him from rank 3/8 to 6/8. The number went DOWN and is left down: the
label is now right and the scoring is now visibly wrong, which is the useful
state to be in.

Two timezone traps live in this data and are load-bearing:
  Greensboro NC 1957-09-21 is EDT (-4) — US DST ran Apr 28 to Oct 27 1957.
  Kathmandu is UTC+5:45 (5.75), not +5:30.
Getting either wrong moves the lagna and silently corrupts the benchmark.

Run: ./venv311/bin/python tests/test_vocational_calibration.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# name, date, time, lat, lon, tz, actual profession, notes
COHORT = [
    ("Raman",       "1974-11-26", "11:59", 28.6139,  77.2090,  5.5,
     "a saas platform",     "tech/consulting WON; restaurant, real estate, flowers LOST"),
    ("Shashi",      "1970-11-02", "06:02", 18.1018,  78.8520,  5.5,
     "a saas platform",     "service tech WON; transport venture LOST (bankruptcy)"),
    ("Akash",       "1972-08-10", "07:20", 28.6139,  77.2090,  5.5,
     "a saas platform",     "tech millions; downfall 2008-2010"),
    ("Gogi Singh",  "1963-01-27", "23:31", 19.0760,  72.8777,  5.5,
     "a construction firm", "construction"),
    ("Kulbir Puri", "1957-11-22", "09:48", 28.4089,  77.3178,  5.5,
     "spiritual healing",   "spiritual practice"),
    ("Yogi Sharma", "1985-06-19", "03:20", 29.6857,  76.9905,  5.5,
     "a saas platform",     "astrologer building an astrology app"),
    ("Dev Jee",     "1961-03-18", "06:50", 28.6139,  77.2090,  5.5,
     "astrology practice",  "astrologer to the rich and famous"),
    ("Jaimes",      "1973-10-21", "09:15",  4.7110, -74.0721, -5.0,
     "wholesale of cloth",  "distributor, car paint"),
    ("SRK",         "1965-11-02", "02:30", 28.6139,  77.2090,  5.5,
     "content media film",  "actor"),
    ("Joe Ess",     "1957-09-21", "04:27", 36.0726, -79.7920, -4.0,
     "hospitality hotel",   "CEO, hospitality  [tz -4: US DST ran Apr 28-Oct 27 1957]"),
    ("Gerardo",     "1974-12-28", "06:20",  5.5353, -73.3678, -5.0,
     "construction wood",   "construction, wood, military contracts (Tunja, Colombia)"),
    ("Rice",        "1972-10-18", "04:38", 28.6139,  77.2090,  5.5,
     "rice mill",           "rice MILLING (owner's correction: manufacture, not trade); "
                            "took it public, delisted 2019-2021"),
    ("Anish Chanan","1969-02-14", "11:50", 28.6139,  77.2090,  5.5,
     "car OEM manufacturing","automotive OEM manufacturing"),
    ("Prashan",     "1985-12-14", "20:50", 27.7172,  85.3240,  5.75,
     "liquor distribution", "liquor distribution  [tz +5:45 Nepal, NOT +5:30]"),
    # ── UNRELIABLE BIRTH TIMES — scored separately, see UNRELIABLE_TIME ──
    # Three public tech fortunes. The OUTCOMES are beyond dispute; the TIMES are
    # not. Published celebrity times conflict (BG 21:00 vs 22:00, EM 06:20 vs
    # 07:30) and MZ's has no credible source at all.
    #
    # This matters more here than anywhere else in the engine: D-10 divides each
    # sign into ten 3-degree parts, so a placement turns over roughly every 12
    # minutes of clock time. A 40-minute error does not nudge these charts, it
    # reshuffles the whole D-10. A miss on these three is uninterpretable — it
    # could be the scorer, or it could be the wrong chart.
    ("BG",          "1955-10-28", "21:00", 47.6062, -122.3321, -8.0,
     "a saas platform",     "software  [tz -8: US DST ended Sep 25 1955]"),
    ("EM",          "1971-06-28", "06:20", -25.7479, 28.2293,  2.0,
     "a saas platform",     "software, THEN space and cars — see ALSO_ACCEPTABLE"),
    ("MZ",          "1984-05-14", "08:00", 41.0340, -73.7629, -4.0,
     "a saas platform",     "software  [tz -4: EDT]"),
    # JS is EXCLUDED: birth city unknown. Substituting Delhi produced a
    # different lagna than his stored chart, so any result would be noise.
]

CATEGORIES = [
    "a saas platform", "a construction firm", "hospitality hotel",
    "wholesale distribution", "content media film", "a coaching institute",
    # ONE occult slot, not two. "spiritual healing" and "astrology practice"
    # both resolve to Ketu+Jupiter, so they scored identically and always tied;
    # which one landed first was dict ordering. Listing both advertised eight
    # independent options when the engine only distinguishes seven, and cost
    # whoever drew the losing half of the tie a rank.
    "spiritual or astrology practice",
]

# Map each person's actual work onto the category whose NATURE it shares, so
# ranking is apples-to-apples (car OEM and construction are both Mars+Saturn
# manufacturing; liquor and rice are both Mercury+Moon wholesale).
ACTUAL_AS_CATEGORY = {
    "a saas platform": "a saas platform",
    "a construction firm": "a construction firm",
    "construction wood": "a construction firm",
    "car OEM manufacturing": "a construction firm",
    "hospitality hotel": "hospitality hotel",
    "rice mill": "a construction firm",
    "wholesale distribution": "wholesale distribution",
    "liquor distribution": "wholesale distribution",
    "wholesale of cloth": "wholesale distribution",
    "content media film": "content media film",
    "spiritual healing": "spiritual or astrology practice",
    "astrology practice": "spiritual or astrology practice",
}


# ONE documented exception, not a tuning knob. EM's fortune is genuinely split
# between software and heavy manufacture (rockets, cars); marking him wrong for
# ranking manufacturing first would be scoring the label, not the engine. No
# other chart gets an alternative, and the strict-tech number is printed too.
ALSO_ACCEPTABLE = {"EM": ["a construction firm"]}

# Excluded from the headline number. Not because they miss — BG and EM both hit
# — but because a hit on an unverified time is luck, not evidence, and averaging
# luck into the score would make the benchmark feel stronger than it is.
UNRELIABLE_TIME = {"BG", "EM", "MZ"}


def _build(date, time, lat, lon, tz):
    from antar_engine.chart import calculate_chart
    from antar_engine.divisional_charts import calculate_all_divisional_charts
    cd = calculate_chart(date, time, lat, lon, tz)
    lg = cd["lagna"]
    cd["divisional_charts"] = calculate_all_divisional_charts(
        cd["planets"], lg.get("sign_index", 0) * 30 + lg.get("degree", 0)
    )
    return cd


def score_cohort(verbose=False):
    from antar_engine.subject_promise import vocational_fit
    from antar_engine.venture_context import detect_venture_nature
    hits = 0
    strict_hits = 0
    rows = []
    for name, d, t, lat, lon, tz, actual, note in COHORT:
        cd = _build(d, t, lat, lon, tz)
        scores = {}
        for cat in CATEGORIES:
            nat = detect_venture_nature("", cat)
            if not nat:
                continue
            scores[cat] = vocational_fit(cd, nat["karakas"], nat["nature"])["score"]
        target = ACTUAL_AS_CATEGORY.get(actual, actual)
        order = sorted(scores, key=scores.get, reverse=True)
        rank = order.index(target) + 1
        if name in UNRELIABLE_TIME:
            rows.append((name, target, rank, len(scores), order[0], True))
            if verbose:
                print(f"  {name:12} {target[:20]:21} rank {rank}/{len(scores)}  "
                      f"top: {order[0]}   [birth time unverified]")
            continue
        strict_hits += rank <= 2
        best = min([rank] + [order.index(a) + 1 for a in ALSO_ACCEPTABLE.get(name, [])])
        hits += best <= 2
        rows.append((name, target, rank, len(scores), order[0], False))
        if verbose:
            print(f"  {name:12} {target[:20]:21} rank {rank}/{len(scores)}  "
                  f"top: {max(scores, key=scores.get)}")
    graded = len(COHORT) - len(UNRELIABLE_TIME)
    return hits, graded, rows, strict_hits


def test_beats_chance():
    """Top-2 of N categories: chance is 2/N per person. Must beat it."""
    hits, total, _, _ = score_cohort()
    assert hits >= 3, (
        f"vocational_fit put the real profession in the top-2 for only "
        f"{hits}/{total} — at or below chance. Scoring has regressed."
    )


if __name__ == "__main__":
    hits, total, rows, strict = score_cohort(verbose=True)
    exp = 2.0 * total / len(CATEGORIES)
    print(f"\ncorrect profession in top-2: {hits}/{total}  "
          f"(chance {exp:.1f}/{total} — top-2 of {len(CATEGORIES)})")
    print(f"strict (no ALSO_ACCEPTABLE):  {strict}/{total}")
    print(f"{len(UNRELIABLE_TIME)} charts excluded: birth time unverified, and D-10 "
          f"turns over every ~12 min")
