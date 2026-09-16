"""
antar_engine/vertical_fit.py

Vertical-Fit engine — WHICH business vertical / commodity has the most potential
for a chart, not just the broad field. Deterministic; the LLM only narrates.

Owner's premise (2026-09-16): every planet "owns" specific commodity sectors, so
two ventures wearing the same "tech" skin can succeed or fail depending on the
COMMODITY's ruling planet (e.g. food-tech/POS is Moon, not Mercury; EV/mobility
is Venus+Mars+Rahu, not Mercury). The chart says which planet's sectors actually
pay — and which are traps.

Method — for each candidate vertical, score its ruling planet(s) across three
charts, each with a DISTINCT job (owner-locked weighting: D-1 leads, D-9 is a
hard durability gate, D-10 confirms the arena):
  D-1  — does this sector MAKE money for me?   promise / wealth-linkage   (LEADS)
  D-9  — does it LAST / deliver?               durability                 (GATE, multiplier)
  D-10 — is it my professional ARENA?          domain-fit                 (confirm, multiplier)
Then: WINNERS clear all three; TRAPS clear D-1 but fail D-9 ("starts well, then
collapses" — the failed-venture signature) or are afflicted. Dasha says WHEN.

v1 significations (VERTICAL_MAP) are a co-designed starting point — refine
against real charts, not a final word.
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import (
    SIGNS, SIGN_LORD, _EXALT, _OWN, _DEBIL, _sign_n_from, _amatyakaraka,
)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
           "Rahu", "Ketu"]

# ── planet → commodity/sector significations (descriptive; co-designed) ──────
# Reference for narration + for extending VERTICAL_MAP; scoring runs off the
# VERTICAL_MAP below (a vertical's ruling planets), not this dict directly.
PLANET_SECTORS = {
    "Sun":     ["government / PSU", "gold", "power & energy", "pharma-authority",
                "administration", "leadership brands"],
    "Moon":    ["food & beverage", "dairy / FMCG", "liquids & water",
                "hospitality", "mass consumer / D2C", "nursing & eldercare"],
    "Mars":    ["engineering & manufacturing", "real estate & construction",
                "machinery & hardware", "defense", "tools", "med-devices / surgery"],
    "Mercury": ["IT & software services", "consulting", "staffing / body-shop",
                "agencies", "trading & brokerage", "marketplaces", "accounting"],
    "Jupiter": ["finance & banking", "law", "advisory / strategy", "education",
                "wealth management", "insurance", "publishing"],
    "Venus":   ["luxury & fashion", "beauty & cosmetics", "jewelry",
                "vehicles / automobiles", "flowers", "entertainment & events",
                "interiors / hospitality-premium"],
    "Saturn":  ["mass production", "steel / iron / mining", "oil",
                "logistics & supply-chain", "agri-commodity", "waste / recycling",
                "infrastructure"],
    "Rahu":    ["deep-tech / AI", "crypto / web3", "aviation",
                "import-export / foreign", "media & virality", "mobility-tech",
                "speculation", "first-mover / unconventional"],
    "Ketu":    ["medicine / healthtech niche", "deep R&D", "security / infra-tech",
                "wellness / occult", "lean / minimalist plays"],
}

# ── vertical → ruling planets (the judgment calls; owner-refined) ────────────
# POS/food-tech = Moon LOCKED by owner (commodity over tech skin).
VERTICAL_MAP = {
    "SaaS / dev tools":                     {"primary": "Mercury", "secondary": ["Rahu"]},
    "Marketplace / aggregator":             {"primary": "Mercury", "secondary": ["Rahu"]},
    "Consulting / staffing / BOT services": {"primary": "Mercury", "secondary": ["Jupiter"]},
    "Fintech / payments":                   {"primary": "Jupiter", "secondary": ["Mercury"]},
    "Finance / banking / advisory":         {"primary": "Jupiter", "secondary": ["Mercury"]},
    "Food-tech / POS / F&B":                {"primary": "Moon",    "secondary": ["Mercury"]},
    "D2C consumer brand":                   {"primary": "Moon",    "secondary": ["Venus"]},
    "EV / mobility":                        {"primary": "Venus",   "secondary": ["Mars", "Rahu"]},
    "Luxury / fashion / beauty":            {"primary": "Venus",   "secondary": ["Mercury"]},
    "Crypto / web3":                        {"primary": "Rahu",    "secondary": ["Saturn"]},
    "Import / export (foreign trade)":      {"primary": "Rahu",    "secondary": ["Mercury"]},
    "Media / creator / gaming":             {"primary": "Rahu",    "secondary": ["Venus"]},
    "Real estate / proptech / construction":{"primary": "Mars",    "secondary": ["Saturn", "Moon"]},
    "Manufacturing / engineering / hardware":{"primary": "Mars",   "secondary": ["Saturn"]},
    "Logistics / supply-chain":             {"primary": "Saturn",  "secondary": ["Mercury", "Mars"]},
    "Healthtech / medicine":                {"primary": "Ketu",    "secondary": ["Sun", "Jupiter"]},
    "Government / energy / gold":           {"primary": "Sun",     "secondary": ["Mars"]},
}

# D-1 wealth/business houses and their weight (does the sector PAY).
WEALTH_HOUSES = {11: 3.0, 2: 2.5, 10: 2.0, 7: 2.0, 3: 1.5, 5: 1.2, 9: 1.0, 1: 1.0}
DUSTHANA = {6, 8, 12}
KENDRA = {1, 4, 7, 10}
TRIKONA = {1, 5, 9}


def _dig_score(planet: str, sign: Optional[str]) -> float:
    """+2 exalted, +1.5 own, -2 debilitated, 0 neutral."""
    if not sign:
        return 0.0
    if _EXALT.get(planet) == sign:
        return 2.0
    if sign in _OWN.get(planet, set()):
        return 1.5
    if _DEBIL.get(planet) == sign:
        return -2.0
    return 0.0


def _d1_wealth(planet, d1, d1_lagna):
    """D-1 wealth-linkage — does this planet's sector make money? (LEADS)"""
    v = d1.get(planet) or {}
    sign, house = v.get("sign"), v.get("house")
    s = 0.0
    why = []
    if house in WEALTH_HOUSES:
        s += WEALTH_HOUSES[house]
        why.append("sits in a wealth/business house")
    for h, w in ((2, 2.0), (11, 2.0), (10, 1.5), (7, 1.5)):
        if SIGN_LORD.get(_sign_n_from(d1_lagna, h)) == planet:
            s += w
            why.append("rules a wealth/business house")
            break
    dg = _dig_score(planet, sign)
    s += dg
    if dg > 0:
        why.append("dignified in the birth chart")
    elif dg < 0:
        why.append("weak in the birth chart")
    if house in DUSTHANA:
        s -= 1.5
        why.append("in a difficult (6/8/12) house")
    elif house in (KENDRA | TRIKONA):
        s += 0.5
    return s, why


def _d9_durability(planet, d1, d9):
    """D-9 durability GATE — does it last? Returns (multiplier, why)."""
    d9sign = ((d9.get("planets") or {}).get(planet) or {}).get("sign")
    d1sign = (d1.get(planet) or {}).get("sign")
    dg = _dig_score(planet, d9sign)
    vargottama = bool(d1sign and d9sign and d1sign == d9sign)
    if dg >= 2.0:
        return 1.30, "holds strong (exalted in the D-9)"
    if vargottama:
        return 1.25, "holds strong (vargottama — same sign in D-1 and D-9)"
    if dg >= 1.5:
        return 1.20, "holds (own sign in the D-9)"
    if dg <= -2.0:
        return 0.55, "does NOT last (weak in the D-9 — starts well, then fades)"
    return 1.0, "steady in the D-9"


def _d10_arena(planet, d1, d10, amk):
    """D-10 arena-fit — is it my professional turf? Returns (multiplier, why)."""
    d10pl = d10.get("planets") or {}
    d10lagna = d10.get("lagna")
    v = d10pl.get(planet) or {}
    d10sign, d10house = v.get("sign"), v.get("house")
    mult = 1.0
    why = []
    if d10house == 10:
        mult += 0.25
        why.append("in the 10th of your career chart")
    elif d10house in KENDRA:
        mult += 0.10
    if d10lagna and SIGN_LORD.get(_sign_n_from(d10lagna, 10)) == planet:
        mult += 0.20
        why.append("rules your career chart's 10th")
    dg = _dig_score(planet, d10sign)
    if dg > 0:
        mult += 0.10
        why.append("dignified in the career chart")
    elif dg < 0:
        mult -= 0.15
    if planet == amk:
        mult += 0.15
        why.append("your career karaka")
    return max(0.6, mult), why


def _afflicted(planet, d1):
    """Trap flags — node shadow, debilitation, or a difficult house."""
    v = d1.get(planet) or {}
    house, sign = v.get("house"), v.get("sign")
    flags = []
    if house in DUSTHANA:
        flags.append("in a difficult house")
    if _DEBIL.get(planet) == sign:
        flags.append("debilitated")
    for node in ("Rahu", "Ketu"):
        if planet not in ("Rahu", "Ketu") and (d1.get(node) or {}).get("house") == house:
            flags.append(f"shadowed by {node}")
    return flags


def analyze_vertical_fit(chart_data: dict, dasha_lords=None) -> dict:
    """Rank business verticals by potential for this chart. Never raises.
    `dasha_lords` = iterable of currently-running maha/antar lord names (timing)."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        d1_lagna = (cd.get("lagna") or {}).get("sign")
        div = cd.get("divisional_charts") or {}
        d9 = div.get("d9") or div.get("D9") or {}
        d10 = div.get("d10") or div.get("D10") or {}
        if not d1 or not d1_lagna or not (d10.get("planets")):
            return {"available": False}

        amk = _amatyakaraka(d1)
        dl = set(dasha_lords or [])

        pscore = {}
        for p in PLANETS:
            d1w, d1why = _d1_wealth(p, d1, d1_lagna)
            d9m, d9why = _d9_durability(p, d1, d9)
            d10m, d10why = _d10_arena(p, d1, d10, amk)
            composite = max(0.0, d1w) * d9m * d10m
            pscore[p] = {
                "d1_wealth": round(d1w, 2),
                "d9_mult": d9m,
                "d10_mult": round(d10m, 2),
                "composite": round(composite, 2),
                "durable": d9m >= 1.0,
                "afflicted": _afflicted(p, d1),
                "active_now": p in dl,
                "why": {"d1": d1why, "d9": d9why, "d10": d10why},
            }

        winners, traps = [], []
        for vert, mp in VERTICAL_MAP.items():
            prim = mp["primary"]
            secs = mp.get("secondary", [])
            pp = pscore[prim]
            score = pp["composite"] + 0.4 * sum(pscore[s]["composite"] for s in secs)
            active = pp["active_now"] or any(pscore[s]["active_now"] for s in secs)
            if active:
                score *= 1.2
            entry = {
                "vertical": vert,
                "ruling": [prim] + secs,
                "score": round(score, 2),
                "durable": pp["durable"],
                "afflicted_by": pp["afflicted"],
                "active_now": active,
            }
            # TRAP: primary looks promising on D-1 but fails the durability gate,
            # or the primary is afflicted → "starts well / high risk".
            if (pp["d1_wealth"] >= 2.0 and not pp["durable"]) or pp["afflicted"]:
                entry["reason"] = (
                    "looks promising but the chart says it won't last"
                    if not pp["durable"]
                    else "the ruling energy is under strain — high risk")
                traps.append(entry)
            else:
                winners.append(entry)

        winners.sort(key=lambda x: -x["score"])
        traps.sort(key=lambda x: -x["score"])

        # [wealth-potential 2026-09-16] OVERALL enterprise-potential band — the
        # "does this chart carry business/wealth potential at all, vs a thin one"
        # read. This is ORDINAL (strong/moderate/thin), NEVER a magnitude/tier
        # ($ amount, billionaire vs millionaire) — that class of claim was
        # empirically falsified (see the D-2/Hora wealth-level study) and is not
        # shipped. Signal = how many planets are BOTH wealth-linked (D-1) AND
        # durable (clear the D-9 gate), plus the strength of the best verticals.
        durable_wealth = [p for p, s in pscore.items()
                          if s["d1_wealth"] >= 2.0 and s["durable"]]
        top3 = sum(w["score"] for w in winners[:3])
        # thresholds are PROVISIONAL — calibrate against known charts before ship.
        potential_score = round(top3 + 1.5 * len(durable_wealth), 2)
        if potential_score >= 14 and len(durable_wealth) >= 3:
            band = "strong"
        elif potential_score >= 8 and len(durable_wealth) >= 2:
            band = "moderate"
        else:
            band = "thin"
        return {
            "available": True,
            "amatyakaraka": amk,
            "potential_band": band,          # strong | moderate | thin (ordinal)
            "potential_score": potential_score,   # internal, for calibration
            "durable_wealth_planets": durable_wealth,
            "winners": winners[:6],
            "traps": traps[:5],
            "planet_scores": pscore,
        }
    except Exception:
        return {"available": False}
