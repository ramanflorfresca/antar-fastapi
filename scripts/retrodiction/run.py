#!/usr/bin/env python3
"""
scripts/retrodiction/run.py — do our dasha rules beat chance on KNOWN life events?

PRE-REGISTERED (written before any result was looked at, 2026-10-10). Four rules,
no more. Adding or changing a rule after seeing results voids the test.

  A  career/business start : Antardasha lord is the 10th lord or sits in the 10th
  B  career/business start : Mahadasha OR Antardasha lord is the 10th lord / in 10th
  C  relationship began    : Antardasha lord is the 7th lord, sits in the 7th, or is Venus
  D  relationship ended    : Antardasha lord is the 7th lord, or lords/sits in 6/8/12

Houses are whole-sign from the Lagna, Lahiri sidereal. "Holds for an event" = the
condition is true on ANY day inside the event's date tolerance.

CHANCE is measured, not assumed: for every person, the same condition is evaluated
at monthly-spaced dates across their adult life (same window width). A rule's
expected hits = the sum, over its events, of that person's chance rate. Observed vs
expected is an exact Poisson-binomial tail. A rule is only called "supported" with
>= MIN_EVENTS events, p < 0.05 AND lift >= 1.25; anything less is reported as
"underpowered" or "no signal" — never as a result. The report also states the
smallest lift this N could ever detect, so a small dataset can't pass off silence
as evidence.

Inputs (CSV, private — gitignored): data/retrodiction/people.csv, events.csv.
Needs pyswisseph. Output: totals only.
"""
from __future__ import annotations

import csv
import math
import os
import sys
from datetime import date, datetime, timedelta

import swisseph as swe

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "retrodiction")
MIN_EVENTS = 20
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars",
             "Jupiter", "Saturn", "Saturn", "Jupiter"]
DASHA = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
YEARS = dict(zip(DASHA, [7, 20, 6, 10, 7, 18, 16, 19, 17]))
NAK_LORD = [DASHA[i % 9] for i in range(27)]
PLANETS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
           "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN}
YEAR_DAYS = 365.25
RULE_FOR = {"business_start": ("A", "B"), "career_start": ("A", "B"),
            "relationship_began": ("C",), "relationship_ended": ("D",)}


def _jd(dt_utc: datetime) -> float:
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600)


def build_person(row: dict) -> dict:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    local = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
    utc = local - timedelta(hours=float(row["tz"]))
    jd = _jd(utc)
    flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
    pos = {n: swe.calc_ut(jd, p, flags)[0][0] % 360 for n, p in PLANETS.items()}
    rahu = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0] % 360
    pos["Rahu"], pos["Ketu"] = rahu, (rahu + 180) % 360
    asc = swe.houses_ex(jd, float(row["lat"]), float(row["lon"]), b"P", swe.FLG_SIDEREAL)[1][0] % 360
    lagna = int(asc // 30)
    house = {n: (int(l // 30) - lagna) % 12 + 1 for n, l in pos.items()}
    lord_of = {h: SIGN_LORD[(lagna + h - 1) % 12] for h in range(1, 13)}
    # Vimsottari: Moon nakshatra -> first MD with the unelapsed balance
    nak = pos["Moon"] / (360 / 27)
    idx = int(nak)
    frac_left = 1 - (nak - idx)
    lord0 = NAK_LORD[idx]
    start = utc - timedelta(days=YEARS[lord0] * (1 - frac_left) * YEAR_DAYS)
    periods, t, k = [], start, DASHA.index(lord0)
    while (t - start).days < 120 * YEAR_DAYS:
        md = DASHA[k % 9]
        md_len = YEARS[md] * YEAR_DAYS
        a = t
        for j in range(9):
            ad = DASHA[(DASHA.index(md) + j) % 9]
            ad_len = md_len * YEARS[ad] / 120
            periods.append((a, a + timedelta(days=ad_len), md, ad))
            a += timedelta(days=ad_len)
        t += timedelta(days=md_len)
        k += 1
    return {"id": row["id"], "birth": utc, "house": house, "lord_of": lord_of, "periods": periods}


def lords_at(p: dict, d: date) -> tuple:
    dt = datetime(d.year, d.month, d.day, 12)
    for s, e, md, ad in p["periods"]:
        if s <= dt < e:
            return md, ad
    return None, None


def holds(rule: str, p: dict, md: str, ad: str) -> bool:
    H, L = p["house"], p["lord_of"]
    in10 = lambda x: x == L[10] or H.get(x) == 10
    if rule == "A":
        return in10(ad)
    if rule == "B":
        return in10(md) or in10(ad)
    if rule == "C":
        return ad == L[7] or H.get(ad) == 7 or ad == "Venus"
    if rule == "D":
        return ad == L[7] or any(ad == L[h] or H.get(ad) == h for h in (6, 8, 12))
    raise ValueError(rule)


def window_holds(rule: str, p: dict, center: date, tol: int) -> bool:
    for off in range(-tol, tol + 1, 15):
        md, ad = lords_at(p, center + timedelta(days=off))
        if ad and holds(rule, p, md, ad):
            return True
    return False


def chance(rule: str, p: dict, tol: int) -> float:
    """Share of random adult-life dates (monthly grid, ages 18-65) where the rule
    would have 'held' under the same window width."""
    b = p["birth"].date()
    hits = n = 0
    d = date(b.year + 18, b.month, min(b.day, 28))
    end = min(date(b.year + 65, b.month, 28), date.today())
    while d < end:
        n += 1
        hits += window_holds(rule, p, d, tol)
        d += timedelta(days=30)
    return hits / n if n else float("nan")


def tail_p(observed: int, probs: list) -> float:
    """P(X >= observed) for a sum of independent Bernoulli(probs)."""
    dist = [1.0]
    for q in probs:
        nxt = [0.0] * (len(dist) + 1)
        for i, v in enumerate(dist):
            nxt[i] += v * (1 - q)
            nxt[i + 1] += v * q
        dist = nxt
    return sum(dist[observed:])


def min_detectable_lift(probs: list) -> float:
    """Smallest lift (observed/expected) a perfect-looking result could reach at
    p<0.05 with these chance rates — if even all-hits can't get there, N is too small."""
    n = len(probs)
    exp = sum(probs)
    for k in range(1, n + 1):
        if tail_p(k, probs) < 0.05:
            return round(k / exp, 2) if exp else float("inf")
    return float("inf")


def main() -> int:
    people = {r["id"]: build_person(r) for r in csv.DictReader(open(os.path.join(DATA, "people.csv")))}
    events = list(csv.DictReader(open(os.path.join(DATA, "events.csv"))))
    print(f"people={len(people)} events={len(events)}  (totals only)\n")
    rules = {"A": "career/business start, AD lord 10th", "B": "career/business start, MD or AD 10th",
             "C": "relationship began, AD 7th/Venus", "D": "relationship ended, AD 7th/6-8-12"}
    for rule, label in rules.items():
        obs, probs, skipped = 0, [], 0
        for e in events:
            if rule not in RULE_FOR.get(e["type"], ()):
                continue
            p = people.get(e["person"])
            if not p:
                skipped += 1
                continue
            tol = int(e.get("tol_days") or 92)
            d = date.fromisoformat(e["date"])
            obs += window_holds(rule, p, d, tol)
            probs.append(chance(rule, p, tol))
        n = len(probs)
        if not n:
            print(f"{rule} {label}: no events"); continue
        exp = sum(probs)
        lift = obs / exp if exp else float("nan")
        pv = tail_p(obs, probs)
        mdl = min_detectable_lift(probs)
        if n < MIN_EVENTS:
            verdict = f"UNDERPOWERED (n={n} < {MIN_EVENTS}); needs lift >= {mdl} to even register"
        elif pv < 0.05 and lift >= 1.25:
            verdict = "SUPPORTED — confirm on a fresh holdout before wiring"
        else:
            verdict = "no signal at this N"
        print(f"{rule} {label}\n   n={n} hit={obs} expected={exp:.1f} lift={lift:.2f} p={pv:.3f} -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
