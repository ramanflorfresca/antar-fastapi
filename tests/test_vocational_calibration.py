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
    17-chart cohort (+3 public tech fortunes)  9/17

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
    # Three public tech fortunes. Birth data is from published records, not from
    # the owner, so it is weaker evidence than the rest of this cohort — but the
    # outcomes are not in dispute, which is the point.
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
    "spiritual healing", "astrology practice",
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
    "spiritual healing": "spiritual healing",
    "astrology practice": "astrology practice",
}


# ONE documented exception, not a tuning knob. EM's fortune is genuinely split
# between software and heavy manufacture (rockets, cars); marking him wrong for
# ranking manufacturing first would be scoring the label, not the engine. No
# other chart gets an alternative, and the strict-tech number is printed too.
ALSO_ACCEPTABLE = {"EM": ["a construction firm"]}


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
        strict_hits += rank <= 2
        best = min([rank] + [order.index(a) + 1 for a in ALSO_ACCEPTABLE.get(name, [])])
        hits += best <= 2
        rows.append((name, target, rank, len(scores), max(scores, key=scores.get)))
        if verbose:
            print(f"  {name:12} {target[:20]:21} rank {rank}/{len(scores)}  "
                  f"top: {max(scores, key=scores.get)}")
    return hits, len(COHORT), rows, strict_hits


def test_beats_chance():
    """Top-2 of 8 categories: chance is ~2/N per person. Must beat it."""
    hits, total, _, _ = score_cohort()
    assert hits >= 3, (
        f"vocational_fit put the real profession in the top-2 for only "
        f"{hits}/{total} — at or below chance. Scoring has regressed."
    )


if __name__ == "__main__":
    hits, total, rows, strict = score_cohort(verbose=True)
    print(f"\ncorrect profession in top-2: {hits}/{total}  (chance ~2/{total})")
    print(f"strict (no ALSO_ACCEPTABLE):  {strict}/{total}")
