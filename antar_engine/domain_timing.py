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


def _sade_sati(chart_data, when):
    """Saturn transiting the 12th / 1st / 2nd from the natal Moon — the classic
    health/pressure period."""
    try:
        from antar_engine import transits as _tr
        d1 = chart_data.get("planets") or {}
        moon_sign = (d1.get("Moon") or {}).get("sign")
        if moon_sign not in SIGNS:
            return False
        mi = SIGNS.index(moon_sign)
        tl = _tr.calculate_transits(chart_data, target_date=when)
        sat = None
        for t in tl:
            if t.get("planet") == "Saturn":
                sat = t.get("sign") or t.get("transit_sign")
        if sat not in SIGNS:
            return False
        return (SIGNS.index(sat) - mi) % 12 in (11, 0, 1)
    except Exception:
        return False


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

        # Parse Vimśottarī MD + AD periods and Chara (jaimini) sign periods once.
        vim = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
        vim_md, vim_ad = [], []
        for p in vim if isinstance(vim, list) else []:
            if not isinstance(p, dict):
                continue
            lvl = str(p.get("level") or p.get("type") or "").lower()
            lord = str(p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("lord") or "").title()
            s = str(p.get("start_date") or p.get("start") or "")[:10]
            e = str(p.get("end_date") or p.get("end") or "")[:10]
            if not (lord and s and e):
                continue
            if lvl in ("mahadasha", "maha", "md"):
                vim_md.append({"lord": lord, "start": s, "end": e})
            elif lvl in ("antardasha", "antar", "ad", "bhukti"):
                vim_ad.append({"lord": lord, "start": s, "end": e})

        jaim = (dashas or {}).get("jaimini") or (dashas or {}).get("chara") or []
        chara = []
        for cp in jaim if isinstance(jaim, list) else []:
            if not isinstance(cp, dict):
                continue
            s = str(cp.get("start_date") or cp.get("start") or "")[:10]
            e = str(cp.get("end_date") or cp.get("end") or "")[:10]
            sign = str(cp.get("planet_or_sign") or cp.get("lord_or_sign") or "").title()
            lvl = str(cp.get("level") or cp.get("type") or "").lower()
            if s and e and sign in SIGNS:
                chara.append({"sign": sign, "start": s, "end": e,
                              "lvl": 2 if lvl in ("antardasha", "ad", "antar") else 1})

        def _active(periods, iso):
            hit = [p for p in periods if p["start"] <= iso <= p["end"]]
            return hit

        prim = houses[0] if houses else None
        chara_weight = spec.get("chara_weight", 0.8)
        horizon = spec.get("horizon_years", 6)
        b = None
        if birth_date:
            try:
                b = datetime.fromisoformat(str(birth_date)[:10])
            except Exception:
                b = None

        # YEAR SCAN — the varshphal is a YEARLY layer, so we judge year by year and
        # let every system vote symmetrically (no single system is the anchor). A
        # year that Chara/varshphal/transit flag surfaces even when Vimśottarī is
        # quiet (the owner's case: "varshphal/Jaimini say yes, the Vim didn't").
        windows = []
        for yr in range(tdt.year, tdt.year + horizon + 1):
            anchor = tdt if yr == tdt.year else datetime(yr, 7, 1)
            iso = anchor.date().isoformat()
            systems, score = [], 0.0

            md = (_active(vim_md, iso) or [{}])[0].get("lord")
            ad = (_active(vim_ad, iso) or [{}])[0].get("lord")
            a_ad, why = _activ(ad) if ad else (0.0, [])
            a_md, why_md = _activ(md) if md else (0.0, [])
            if a_ad >= 1.0 or a_md >= 1.0:
                systems.append(f"Vimśottarī: {md}–{ad} — {(why or why_md or ['activates ' + noun])[0]}")
                score += 1.0

            th = _transit_trigger(cd, anchor, target_signs, transit_grahas)
            if th:
                systems.append("Transits: " + "; ".join(th[:3]))
                score += 1.0

            if b:
                try:
                    age = yr - b.year - (1 if (anchor.month, anchor.day) < (b.month, b.day) else 0)
                    occ = _varsh_hit(cd, age, varsh_houses, malefic_varsh)
                    if occ:
                        systems.append(f"Lal-Kitab varshphal: {', '.join(occ)} in a house of {noun} this year")
                        score += spec.get("varsh_weight", 1.0)
                except Exception:
                    pass

            if spec.get("sade_sati") and _sade_sati(cd, anchor):
                systems.append("Sade Sati — Saturn's pressure over your Moon is active")
                score += spec.get("sade_sati_weight", 1.0)

            cact = _active(chara, iso)
            if cact and prim:
                csign = sorted(cact, key=lambda x: -x["lvl"])[0]["sign"]
                di = SIGNS.index(csign)
                prim_sign = SIGNS[(di + prim - 1) % 12]
                natal_prim = _sign_n_from(lagna, prim)
                chit = None
                if prim_sign == natal_prim or csign == natal_prim:
                    chit = f"its {prim}th aligns your natal {prim}th"
                else:
                    for pl_name in list(karakas) + list(activator_lords):
                        ps = (d1.get(pl_name) or {}).get("sign")
                        if ps and ((SIGNS.index(ps) - di) % 12 + 1) == prim:
                            chit = f"{pl_name} sits in the {prim}th from it"
                            break
                if chit:
                    systems.append(f"Chara dasha ({csign} as lagna): {chit}")
                    score += chara_weight

            if score >= min_score and len(systems) >= 2:
                windows.append({"label": f"{md}–{ad}", "start": f"{yr}-01-01",
                                "end": f"{yr}-12-31", "year": yr, "systems": systems,
                                "score": round(score, 2), "why": why or why_md})

        # nearest-first: every listed window already cleared the convergence bar,
        # so the NEAREST is the actionable one for a "when" question (Andres's live
        # 2025 debt matter should lead, not a stronger 2030 property window). Keep
        # the single strongest separately for callers that want it.
        windows.sort(key=lambda w: w["start"])
        best = windows[0] if windows else None
        strongest = max(windows, key=lambda w: w["score"]) if windows else None
        return {"available": True, "windows": windows[:6], "best": best,
                "strongest": strongest, "convergence": (best["score"] if best else 0)}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
