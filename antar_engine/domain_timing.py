"""
antar_engine/domain_timing.py

Generic multi-system event-timing CONVERGENCE for a life domain — the same method
the relationship engine validated (Vimśottarī antardasha + transits + Chara-as-
lagna + Lal-Kitab varshphal), generalized so legal / health / residence (and any
future domain) all share one proven timer. Only the significators change.

A domain SPEC declares:
  houses           — the domain's houses (from lagna), e.g. legal = [6,7,8,12]
  activator_houses — houses whose LORDS activate the domain when their dasha runs
  karakas          — planet karakas for the domain (Saturn/Mars for legal, …)
  varsh_houses     — Lal-Kitab varshphal houses that light the domain that year
  transit_grahas   — slow movers whose transit triggers (Saturn/Mars/Rahu/Ketu)
  transit_houses   — natal houses a transit graha hitting = a trigger
  malefic_varsh    — if True, only malefics in the varshphal house count (risk)
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.relationships import _house_of, _sign_aspects

_MAL = {"Rahu", "Ketu", "Saturn", "Mars", "Sun"}


def _house_lords(lagna: str, houses) -> set:
    out = set()
    for h in houses:
        s = _sign_n_from(lagna, h)
        if s:
            out.add(SIGN_LORD.get(s))
    return {x for x in out if x}


def _transit_trigger(chart_data, when, target_signs, grahas):
    hits = []
    try:
        from antar_engine import transits as _tr
        tl = _tr.calculate_transits(chart_data, target_date=when)
        pos = {t.get("planet"): (t.get("sign") or t.get("transit_sign")) for t in tl}
        for g in grahas:
            gs = pos.get(g)
            if not gs:
                continue
            for label, tsign in target_signs.items():
                if tsign and (gs == tsign or _sign_aspects(gs, tsign, g)):
                    hits.append(f"{g} presses your {label}")
                    break
    except Exception:
        pass
    return hits


def _varsh_hit(chart_data, age, houses, malefic_only):
    try:
        from antar_engine.lal_kitab import calculate_varshphal_chart
        vp = calculate_varshphal_chart(chart_data, age)
        pl = getattr(vp, "placements", {}) or {}
        occ = [p for p, h in pl.items() if h in houses and (not malefic_only or p in _MAL)]
        return occ
    except Exception:
        return []


def domain_convergence(chart_data: dict, dashas: dict, spec: dict,
                       birth_date: Optional[str] = None, today: Optional[str] = None) -> dict:
    """Return {available, windows[], best, summary}. Each window: {label, start,
    end, systems[], score, why[]}. Never raises."""
    try:
        from datetime import date, datetime
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not d1 or not lagna:
            return {"available": False}
        today = today or date.today().isoformat()
        tdt = datetime.fromisoformat(today[:10])

        houses = spec.get("houses", [])
        karakas = set(spec.get("karakas", []))
        activator_lords = _house_lords(lagna, spec.get("activator_houses", houses))
        varsh_houses = spec.get("varsh_houses", [houses[0]] if houses else [])
        malefic_varsh = spec.get("malefic_varsh", True)
        transit_grahas = spec.get("transit_grahas", ["Saturn", "Mars", "Rahu"])
        transit_houses = spec.get("transit_houses", houses)
        min_score = spec.get("min_score", 2.0)
        noun = spec.get("noun", "this matter")

        # transit targets = the SIGNS of the chosen natal houses
        target_signs = {}
        for h in transit_houses:
            s = _sign_n_from(lagna, h)
            if s:
                target_signs[f"house {h} of {noun}"] = s

        def _activ(lord):
            s, why = 0.0, []
            if lord in karakas:
                s += 1.2
                why.append(f"a key planet for {noun} runs")
            if lord in activator_lords:
                s += 1.0
                why.append(f"rules a house of {noun}")
            if _house_of(lord, d1) in houses:
                s += 0.6
                why.append(f"sits in a house of {noun}")
            return s, why

        vim = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
        ads = []
        for p in vim if isinstance(vim, list) else []:
            if not isinstance(p, dict):
                continue
            if str(p.get("level") or p.get("type") or "").lower() not in ("antardasha", "antar", "ad", "bhukti"):
                continue
            lord = str(p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("lord") or "").title()
            parent = str(p.get("parent_lord") or p.get("mahadasha_lord") or "").title()
            s = str(p.get("start_date") or p.get("start") or "")[:10]
            e = str(p.get("end_date") or p.get("end") or "")[:10]
            if lord and s and e:
                ads.append({"lord": lord, "parent": parent, "start": s, "end": e})
        ads.sort(key=lambda x: x["start"])

        windows = []
        for ad in ads:
            if ad["end"] < today or ad["start"] > str(tdt.year + 6):
                continue
            a_ad, why = _activ(ad["lord"])
            a_md, _ = _activ(ad["parent"]) if ad["parent"] else (0.0, [])
            if a_ad + 0.4 * a_md < 1.5:
                continue
            wstart = datetime.fromisoformat(ad["start"])
            anchor = max(wstart, tdt)
            systems = [f"Vimśottarī: {ad['parent']}–{ad['lord']} — {why[0] if why else 'activates ' + noun}"]
            score = 1.0

            th = _transit_trigger(cd, anchor, target_signs, transit_grahas)
            if th:
                systems.append("Transits: " + "; ".join(th[:3]))
                score += 1.0

            if birth_date:
                try:
                    b = datetime.fromisoformat(str(birth_date)[:10])
                    age = anchor.year - b.year - (1 if (anchor.month, anchor.day) < (b.month, b.day) else 0)
                    occ = _varsh_hit(cd, age, varsh_houses, malefic_varsh)
                    if occ:
                        systems.append(f"Lal-Kitab varshphal: {', '.join(occ)} in a house of {noun} this year")
                        score += 1.0
                except Exception:
                    pass

            # Chara — dasha sign as lagna: a karaka/malefic in the primary domain
            # house counted FROM the dasha sign.
            jaim = (dashas or {}).get("jaimini") or (dashas or {}).get("chara") or []
            prim = houses[0] if houses else None
            for cp in jaim if isinstance(jaim, list) else []:
                if not isinstance(cp, dict):
                    continue
                s = str(cp.get("start_date") or cp.get("start") or "")[:10]
                e = str(cp.get("end_date") or cp.get("end") or "")[:10]
                csign = str(cp.get("planet_or_sign") or cp.get("lord_or_sign") or "").title()
                if s and e and s <= anchor.date().isoformat() <= e and csign in SIGNS and prim:
                    di = SIGNS.index(csign)
                    for pl_name in list(karakas) + list(_MAL):
                        ps = (d1.get(pl_name) or {}).get("sign")
                        if ps and ((SIGNS.index(ps) - di) % 12 + 1) == prim:
                            systems.append(f"Chara dasha ({csign} as lagna): {pl_name} sits in the {prim}th from it")
                            score += 0.8
                            break
                    break

            windows.append({"label": f"{ad['parent']}–{ad['lord']}", "start": ad["start"],
                            "end": ad["end"], "systems": systems, "score": round(score, 2),
                            "why": why})

        windows.sort(key=lambda w: (-w["score"], w["start"]))
        best = windows[0] if windows and windows[0]["score"] >= min_score else None
        return {"available": True, "windows": windows[:5], "best": best,
                "convergence": (best["score"] if best else 0)}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
