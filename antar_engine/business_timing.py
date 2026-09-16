"""
antar_engine/business_timing.py

Business-Timing / Dasha-Fortune engine — is NOW a strong window to build a
business boldly, or a period to consolidate and protect? Deterministic; the LLM
only narrates.

WHY this and not "which vertical": blind-validation against two real charts with
dated outcomes (2026-09-16) showed venture fortune tracks the DIGNITY OF THE
RUNNING DASHA LORD, not the sector's natal planet — and the naive sector model
was actively misleading (it rated the exact failed sectors high). See:
  - Akash: tech-services BOOM 2003-09 = strong Moon mahadasha; food-tech STRUGGLE
    2020+ = weak/afflicted Rahu mahadasha.
  - Shashi: consulting BOOM 2016-19 = Sun MD carried by a strong antardasha; auto
    DOWNFALL 2019+ = debilitated Moon mahadasha (the 2019 pivot walked into the
    first year of a low-fortune decade).
Magnitude/tier claims (billionaire vs millionaire) are NOT made — that class was
empirically falsified (D-2 wealth study). This engine speaks to TIMING and the
ordinal fortune of a period, never a net-worth level.

Model: period_fortune = 0.6*fortune(MD lord) + 0.4*fortune(AD lord), where
fortune(planet) combines D-1 dignity + house placement + D-9 dignity/vargottama
- affliction (node shadow / dusthana / debilitation). Bands: strong (build) /
mixed (proceed measured) / lean (consolidate, avoid capital-heavy bets).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from antar_engine.d10_career import (
    SIGNS, SIGN_LORD, _EXALT, _OWN, _DEBIL, _sign_n_from,
)

KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}
MALEFIC = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}


def _dig(planet, sign):
    if not sign:
        return 0.0
    if _EXALT.get(planet) == sign:
        return 2.0
    if sign in _OWN.get(planet, set()):
        return 1.5
    if _DEBIL.get(planet) == sign:
        return -2.0
    return 0.0


def _placement(planet, house):
    """Nature-aware house strength. Malefics/nodes THRIVE in upachaya (3/6/11) —
    a malefic in the 6th is Harsha (conquers enemies/debts/competition), NOT a
    dusthana weakness; benefics in 6/8/12 are genuinely weakened. (Owner-corrected
    2026-09-16 — Rahu-in-6th is good; mirrors the health engine's Harsha rule.)"""
    if house is None:
        return 0.0, ""
    mal = planet in MALEFIC
    if house == 11:                     # labha — gains, good for all
        return 1.0, "in the house of gains"
    if house == 6:                      # Harsha for malefics; weak for benefics
        return (1.0, "strong in the 6th (conquers competition/debts)") if mal else (-1.5, "weak in a difficult house")
    if house == 3:                      # upachaya, mild
        return (0.8, "gains in a growth house") if mal else (0.3, "")
    if house in KENDRA_TRIKONA:         # angles/trines
        return (0.5, "") if mal else (1.0, "well-placed (angle/trine)")
    if house == 2:                      # wealth
        return (0.6 if mal else 1.0), "in a wealth house"
    if house == 8:                      # mixed for all (research/OPM but turbulent)
        return (-0.3 if mal else -1.0), ("mixed — 8th house")
    if house == 12:                     # loss/foreign
        return (-0.5 if mal else -1.5), "in a house of loss"
    return 0.0, ""


def planet_fortune(planet: str, chart_data: dict) -> dict:
    """Ordinal 'how well-disposed is this dasha lord for this person' score.
    Returns {score, band, reasons[]}. Higher = a more prosperous period when this
    planet's dasha runs."""
    cd = chart_data or {}
    d1 = cd.get("planets") or {}
    div = cd.get("divisional_charts") or {}
    d9 = (div.get("d9") or div.get("D9") or {}).get("planets") or {}
    v = d1.get(planet) or {}
    sign, house = v.get("sign"), v.get("house")
    score = 0.0
    reasons = []

    dg = _dig(planet, sign)
    score += dg
    if dg >= 1.5:
        reasons.append("dignified in the birth chart")
    elif dg <= -2.0:
        reasons.append("weak (debilitated) in the birth chart")

    ps, pr = _placement(planet, house)
    score += ps
    if pr:
        reasons.append(pr)

    d9sign = (d9.get(planet) or {}).get("sign")
    d9dg = _dig(planet, d9sign)
    if d9dg > 0 or (sign and d9sign and sign == d9sign):
        score += 1.0
        reasons.append("holds strength in the D-9")
    elif d9dg < 0:
        score -= 1.0
        reasons.append("loses strength in the D-9")

    # [era-aware 2026-09-16] Rahu is a PRIMARY force of the modern era (Kali Yuga),
    # not a plain malefic. Conjunct Rahu AMPLIFIES a planet's worldly power —
    # Sun→authority/power, Venus→wealth/luxury, Mercury→tech/media/trade, Mars→drive
    # — most of all in wealth/gain/trine houses (Rahu+Venus = enormous wealth,
    # Sun+Rahu = power). It is NOT a flat affliction. Ketu still withdraws; Rahu on
    # the Moon can unsettle the mind (mild caution only).
    if planet not in ("Rahu", "Ketu") and house is not None:
        if (d1.get("Rahu") or {}).get("house") == house:
            if planet == "Moon":
                score -= 0.4; reasons.append("Rahu unsettles the emotional mind")
            elif planet == "Jupiter":
                score += 0.3; reasons.append("Rahu turns the wisdom unconventional (guru-chandala)")
            else:
                amp = 1.2 if house in (2, 5, 9, 10, 11) else 0.8
                score += amp
                reasons.append(f"Rahu amplifies your {planet.lower()} — modern-era power/wealth")
        if (d1.get("Ketu") or {}).get("house") == house and planet != "Sun":
            score -= 0.6; reasons.append("Ketu pulls this toward detachment")

    # [era-aware] Rahu itself is a wealth/gain amplifier where it sits in a
    # wealth/gain/trine/career house — the engine of modern self-made fortune.
    if planet == "Rahu" and house in (2, 5, 9, 10, 11):
        score += 0.8
        reasons.append("Rahu drives gains here (modern-era amplifier)")

    band = "strong" if score >= 2.0 else ("lean" if score <= -1.0 else "mixed")
    return {"score": round(score, 2), "band": band, "reasons": reasons}


def _parse_d(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _rows(dashas, level_names):
    out = []
    for r in (dashas or {}).get("vimsottari", []) or []:
        lvl = r.get("level") or r.get("type") or ""
        if lvl in level_names:
            s = _parse_d(r.get("start_date") or r.get("start"))
            e = _parse_d(r.get("end_date") or r.get("end"))
            lord = r.get("lord_or_sign") or r.get("planet_or_sign")
            if s and e and lord:
                out.append({"lord": lord, "start": s, "end": e})
    out.sort(key=lambda x: x["start"])
    return out


_BAND_LABEL = {
    "strong": "a build-boldly window",
    "mixed": "a measured window — proceed, but don't over-extend",
    "lean": "a consolidate window — protect capital, avoid capital-heavy bets",
}


def dasha_fortune(chart_data: dict, dashas: dict, today: Optional[date] = None,
                  horizon_years: int = 12) -> dict:
    """Current business-timing read + forward windows. Never raises."""
    try:
        today = today or date.today()
        cd = chart_data or {}
        if not (cd.get("planets")):
            return {"available": False}

        # cache each planet's fortune once
        fort = {p: planet_fortune(p, cd) for p in
                ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
                 "Rahu", "Ketu"]}

        maha = _rows(dashas, ("mahadasha",))
        antar = _rows(dashas, ("antardasha", "antar"))

        def _md_lord_at(d):
            for m in maha:
                if m["start"] <= d <= m["end"]:
                    return m["lord"]
            return None

        def _period_fortune(md_lord, ad_lord):
            fm = fort.get(md_lord, {}).get("score", 0.0)
            fa = fort.get(ad_lord, {}).get("score", 0.0)
            s = 0.6 * fm + 0.4 * fa
            return s, ("strong" if s >= 1.2 else ("lean" if s <= -0.6 else "mixed"))

        # build an antardasha-resolution forward timeline, merged into windows
        windows = []
        end_horizon = date(today.year + horizon_years, today.month, today.day)
        cur = None
        for a in antar:
            if a["end"] < today or a["start"] > end_horizon:
                continue
            md_lord = _md_lord_at(a["start"]) or _md_lord_at(a["end"])
            if not md_lord:
                continue
            s, band = _period_fortune(md_lord, a["lord"])
            seg = {"start": a["start"], "end": a["end"], "md": md_lord,
                   "ad": a["lord"], "score": round(s, 2), "band": band}
            if a["start"] <= today <= a["end"]:
                cur = seg
            # merge consecutive same-band segments
            if windows and windows[-1]["band"] == band and windows[-1]["md"] == md_lord:
                windows[-1]["end"] = a["end"]
            else:
                windows.append(dict(seg))

        # current read
        cur_md = _md_lord_at(today)
        cur = cur or (windows[0] if windows else None)
        current = None
        if cur:
            current = {
                "band": cur["band"],
                "label": _BAND_LABEL[cur["band"]],
                "md_lord": cur["md"], "ad_lord": cur["ad"],
                "md_fortune": fort.get(cur["md"], {}),
                "runs_until": cur["end"].isoformat(),
            }

        # next turning point = first upcoming window whose band differs from current
        turning = None
        if current:
            for w in windows:
                if w["start"] > today and w["band"] != current["band"]:
                    turning = {"band": w["band"], "label": _BAND_LABEL[w["band"]],
                               "starts": w["start"].isoformat(),
                               "md_lord": w["md"], "ad_lord": w["ad"]}
                    break

        # the strongest upcoming build window (for "when to go big")
        best = None
        for w in windows:
            if w["band"] == "strong" and w["end"] >= today:
                if best is None or w["score"] > best["score"]:
                    best = w
        best_window = None
        if best:
            best_window = {"start": max(best["start"], today).isoformat(),
                           "end": best["end"].isoformat(),
                           "md_lord": best["md"], "ad_lord": best["ad"],
                           "score": best["score"]}

        # soft, low-confidence temperament lean (NOT a specific-vertical promise):
        # both validation cases won asset-light services and lost capital-heavy
        # product. If the strong lords are the service/advisory set, lean asset-light.
        strong_lords = [p for p, f in fort.items() if f["band"] == "strong"]
        service_set = {"Mercury", "Jupiter", "Saturn"}
        heavy_set = {"Venus", "Mars"}
        if strong_lords and set(strong_lords) & service_set and not (set(strong_lords) & heavy_set):
            lean = "asset-light (services, advisory, digital) over capital-heavy product"
        elif strong_lords and set(strong_lords) & heavy_set:
            lean = "you can carry a product/asset play, but keep it capital-light until a strong window"
        else:
            lean = "keep any new venture lean and low-capital"

        return {
            "available": True,
            "current": current,
            "next_turning_point": turning,
            "best_build_window": best_window,
            "temperament_lean": lean,          # soft, low-confidence
            "planet_fortune": fort,
            "windows": [
                {"start": w["start"].isoformat(), "end": w["end"].isoformat(),
                 "band": w["band"], "md": w["md"], "ad": w["ad"], "score": w["score"]}
                for w in windows
            ],
        }
    except Exception:
        return {"available": False}
