"""
antar_engine/ask_promise.py — Ask/predict Stage 1: the PROMISE assessment.

Classical two-stage prediction: (1) is the event even PROMISED by the chart,
and how strongly? (2) only then, WHEN does it ripen (dashas + transits). Today's
Ask engine does Stage 2 only (timing locks), so it can hand back a confident
window for an event the chart never promised — "over-claimed confidence".

This module is Stage 1. It scores a promise in [0,1] for a concern from four
classical evidences:
  1. Karaka dignity (D1) — the natural significator's strength + dusthana penalty
  2. House-lord dignity + Sarvashtakavarga bindus of the primary concern house
  3. Relevant yogas (dhana/raja/kalatra/putra … or arishta/dosha the other way)
  4. Divisional confirmation — the varga that rules the matter (D9 marriage,
     D10 career, D2 wealth, D7 children …) must corroborate

Confidence downstream = promise × timing (see ask_consultation). Per the product
philosophy the promise is a DIAL, never a hard gate: a weak/absent promise
softens the tone and shifts weight onto agency (remedy/practice), it never says
"you don't have this". agency_weight = 1 - promise is returned for exactly that.

Pure + fail-open: any missing data degrades a factor, never raises. Decoupled
from ask_consultation (no circular import) — the caller passes houses + karakas.
"""
from __future__ import annotations
from typing import List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# dignity string (from antar_ephemeris._planet_strength) -> points
DIGNITY_PTS = {"exalted": 2, "own": 2, "friendly": 1, "neutral": 0,
               "debilitated": -2}

# concern -> the divisional chart that rules the matter (Stage-1 confirmation)
CONCERN_VARGA = {
    "finance": 2, "funding": 2, "wealth": 2, "loss": 2, "speculation": 2,
    "career": 10, "business": 10,
    "marriage": 9, "love": 9, "divorce": 9, "reconciliation": 9,
    "children": 7,
    "property": 4, "domestic_move": 4, "foreign_move": 4,
    "education": 24, "health": 30, "foreign": 9, "legal": 9,
    "spiritual": 20, "general": 9,
}

# concern -> yoga name/category keywords that count as "promising" this matter
_CONCERN_YOGA_HINTS = {
    "finance": ["dhana", "lakshmi", "wealth", "raja"],
    "funding": ["dhana", "raja"],
    "wealth": ["dhana", "lakshmi", "raja"],
    "speculation": ["dhana", "raja"],
    "career": ["raja", "amala", "authority", "dhana"],
    "business": ["dhana", "raja"],
    "marriage": ["kalatra", "relationship", "venus"],
    "love": ["venus", "relationship"],
    "reconciliation": ["venus", "relationship"],
    "children": ["putra", "santan", "jupiter"],
    "property": ["vahana", "home", "property"],
    "education": ["saraswati", "vidya", "budh"],
    "health": ["ayush"],
    "spiritual": ["pravrajya", "moksha", "sanyasa"],
}


def _house_of(sign: str, lagna_idx: int) -> Optional[int]:
    if sign not in SIGNS:
        return None
    return (SIGNS.index(sign) - lagna_idx) % 12 + 1


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _yoga_relevant(concern: str, cat: str, name: str, involved: list,
                   karakas: list, concern_lords: list) -> bool:
    hints = _CONCERN_YOGA_HINTS.get(concern, [])
    blob = (cat + " " + name).lower()
    if any(h in blob for h in hints):
        return True
    inv = set(involved or [])
    return bool(inv & set(karakas)) or bool(inv & set(concern_lords))


def assess_promise(chart_data: dict, houses: List[int], karakas: List[str],
                   *, concern: str = "general") -> dict:
    """Score the chart's PROMISE for `concern` in [0,1] + band + agency_weight
    + an audit `factors` trail. Fail-open: returns promise=None if unassessable."""
    out = {"promise": None, "band": None, "agency_weight": None, "factors": []}
    try:
        from antar_engine.antar_ephemeris import _planet_strength, divisional_chart
    except Exception:
        return out
    try:
        planets = (chart_data or {}).get("planets") or {}
        lagna = (chart_data or {}).get("lagna") or {}
        lagna_sign = lagna.get("sign") if isinstance(lagna, dict) else None
        if lagna_sign not in SIGNS or not planets:
            return out
        lagna_idx = SIGNS.index(lagna_sign)
        houses = list(houses or []) or [10]
        karakas = list(karakas or []) or ["Jupiter"]
        h0 = houses[0]
        concern_lords = [SIGN_LORDS[SIGNS[(lagna_idx + h - 1) % 12]] for h in houses]

        factors = []
        comps = []  # (weight, value in [-1, 1])

        # ── 1. Karaka dignity (D1) ──────────────────────────────────────────
        kpts = []
        for k in karakas:
            sgn = (planets.get(k) or {}).get("sign")
            if sgn not in SIGNS:
                continue
            d = _planet_strength(k, sgn)
            p = DIGNITY_PTS.get(d, 0)
            kh = _house_of(sgn, lagna_idx)
            if kh in (6, 8, 12):
                p -= 1
            kpts.append(p)
            factors.append({"stage": "promise", "factor": f"karaka {k}",
                            "detail": f"{d}, in house {kh}", "points": p})
        if kpts:
            comps.append((0.30, _clamp((sum(kpts) / len(kpts)) / 2.0)))

        # ── 2. Primary house-lord dignity + Sarva bindus (D1) ───────────────
        hl = SIGN_LORDS[SIGNS[(lagna_idx + h0 - 1) % 12]]
        hlpts = 0
        det = []
        hlsgn = (planets.get(hl) or {}).get("sign")
        if hlsgn in SIGNS:
            d = _planet_strength(hl, hlsgn)
            hlpts += DIGNITY_PTS.get(d, 0)
            det.append(f"lord {hl} {d}")
        try:
            from antar_engine.ashtakavarga import get_sarva_strength
            b = get_sarva_strength((lagna_idx + h0 - 1) % 12, chart_data).get("bindus")
            if isinstance(b, (int, float)):
                if b >= 30:
                    hlpts += 1; det.append(f"{b} bindus (strong)")
                elif b <= 24:
                    hlpts -= 1; det.append(f"{b} bindus (weak)")
                else:
                    det.append(f"{b} bindus")
        except Exception:
            pass
        comps.append((0.25, _clamp(hlpts / 3.0)))
        factors.append({"stage": "promise", "factor": f"house {h0}",
                        "detail": ", ".join(det) or "no data", "points": hlpts})

        # ── 3. Relevant yogas ───────────────────────────────────────────────
        try:
            from antar_engine.yogas import detect_all_yogas
            net = 0.0
            for y in (detect_all_yogas(planets, lagna_sign) or []):
                cat = (y.get("category") or "").lower()
                nm = y.get("name") or ""
                if not _yoga_relevant(concern, cat, nm, y.get("involved_planets") or [],
                                      karakas, concern_lords):
                    continue
                neg = any(t in cat or t in nm.lower()
                          for t in ("arishta", "dosha", "negative", "daridra"))
                s = y.get("strength")
                mag = max(0.3, min(1.5, float(s))) if isinstance(s, (int, float)) else 1.0
                net += (-mag if neg else mag)
                factors.append({"stage": "promise", "factor": f"yoga {nm}",
                                "detail": cat or "", "points": (-1 if neg else 1)})
            if net != 0:
                comps.append((0.20, _clamp(0.5 * net)))
        except Exception:
            pass

        # ── 4. Divisional confirmation ──────────────────────────────────────
        try:
            div = CONCERN_VARGA.get(concern, 9)
            dch = divisional_chart(chart_data, div)
            dpts = []
            for k in karakas:
                dstr = (dch.get(k) or {}).get("strength")
                if dstr:
                    dpts.append(DIGNITY_PTS.get(dstr, 0))
            if dpts:
                avg = sum(dpts) / len(dpts)
                comps.append((0.25, _clamp(avg / 2.0)))
                factors.append({"stage": "promise", "factor": f"D{div} confirmation",
                                "detail": f"karaka avg {round(avg, 1)}",
                                "points": round(avg, 1)})
        except Exception:
            pass

        if not comps:
            return out
        tw = sum(w for w, _ in comps)
        signed = sum(w * v for w, v in comps) / tw          # [-1, 1]
        promise = round((signed + 1) / 2, 3)                # [0, 1]
        band = ("strong" if promise >= 0.66 else
                "moderate" if promise >= 0.5 else
                "weak" if promise >= 0.34 else "absent")
        out.update({"promise": promise, "band": band,
                    "agency_weight": round(1 - promise, 3), "factors": factors})
    except Exception as e:
        out["error"] = str(e)
    return out
