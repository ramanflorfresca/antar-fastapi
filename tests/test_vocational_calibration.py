"""
tests/test_vocational_calibration.py
Real people, real professions — the benchmark vocational_fit is measured on.

Ten charts supplied by the product owner, who knows the actual outcomes,
including the unglamorous ones ("surviving, not big"). That is worth more than
a celebrity list: it contains FAILURES, and failures are what discriminate.

Purpose is measurement, not a pass/fail gate. The scoring is not good yet.
The point is that any change to vocational_fit must MOVE THIS NUMBER, and a
regression is visible immediately instead of shipping on a hunch.

Baseline (2026-07-21), correct profession in the engine's top-2 of 8 categories,
chance is ~2/9:
    sign-dignity scoring (original)            2/9
    contextual_strength + Ketu severance       5/9

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
    # JS is EXCLUDED: birth city unknown. Substituting Delhi produced a
    # different lagna than his stored chart, so any result would be noise.
]

CATEGORIES = [
    "a saas platform", "a construction firm", "a restaurant",
    "wholesale of cloth", "content media film", "a coaching institute",
    "spiritual healing", "astrology practice",
]


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
    rows = []
    for name, d, t, lat, lon, tz, actual, note in COHORT:
        cd = _build(d, t, lat, lon, tz)
        scores = {}
        for cat in CATEGORIES:
            nat = detect_venture_nature("", cat)
            if not nat:
                continue
            scores[cat] = vocational_fit(cd, nat["karakas"], nat["nature"])["score"]
        rank = sorted(scores, key=scores.get, reverse=True).index(actual) + 1
        hits += rank <= 2
        rows.append((name, actual, rank, len(scores), max(scores, key=scores.get)))
        if verbose:
            print(f"  {name:12} {actual[:20]:21} rank {rank}/{len(scores)}  "
                  f"top: {max(scores, key=scores.get)}")
    return hits, len(COHORT), rows


def test_beats_chance():
    """Top-2 of 8 categories: chance is ~2/9. Must beat it."""
    hits, total, _ = score_cohort()
    assert hits >= 3, (
        f"vocational_fit put the real profession in the top-2 for only "
        f"{hits}/{total} — at or below chance. Scoring has regressed."
    )


if __name__ == "__main__":
    hits, total, rows = score_cohort(verbose=True)
    print(f"\ncorrect profession in top-2: {hits}/{total}  (chance ~2/{total})")
