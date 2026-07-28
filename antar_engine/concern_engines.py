"""
antar_engine/concern_engines.py

Concern-specific DETERMINISTIC analysis — the "does the promise exist, and is it
lit right now" layer that sits under the timing convergence. Same discipline as
d10_career: read the real chart, score it, hand the narrator FACTS. The LLM
never invents the astrology.

Each concern encodes the classical significator set (per the owner's method):
  funding/loan   — 8th (OTHER people's money: loans, investment, funding),
                   11th (gains), 6th (loans/debt taken), 2nd (own wealth);
                   karakas Jupiter/Venus/Mercury + Rahu (sudden/foreign money);
                   confirm in D-9; is outside money supported + lit by dasha?
  relationship   — 7th (partnership/marriage), 5th (romance), 11th (fulfilment
   (entry)         of desire); karaka Venus (+ Jupiter for a husband); D-9 is the
                   marriage chart; can a significant person enter + is it lit?
  separation     — 7th (partner) AFFLICTED, 6th (discord), 8th (upheaval),
                   12th (loss/bed); karakas Venus/Moon; malefic-driven (RISK);
                   confirm in D-9; is strain/separation elevated + lit?
  health         — 1st (vitality/body), 6th (disease), 8th (chronic/surgery),
                   12th (hospitalisation); karakas Sun/Moon (vitality),
                   Mars/Saturn (affliction); RISK polarity; confirm in D-9.

A significator that is (a) dignified, (b) confirmed in D-9, and (c) active in the
current dasha is the real signal — that convergence is what each verdict weighs.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _EXALT, _OWN, _sign_n_from

_DEBIL = {p: SIGNS[(SIGNS.index(s) + 6) % 12] for p, s in _EXALT.items()}
_DUSTHANA = {6, 8, 12}
_MALEFICS = {"Mars", "Saturn", "Rahu", "Ketu", "Sun"}

# concern → spec. polarity: "gain" (is the good thing supported?) or
# "risk" (is the bad thing elevated?). houses ordered by importance.
CONCERN_SPEC = {
    "funding": {
        "polarity": "gain", "varga": "d9",
        "houses": [8, 11, 6, 2],
        "house_meaning": {8: "other people's money — loans, investment, funding",
                          11: "gains and what comes in", 6: "loans and debt taken on",
                          2: "your own capital"},
        "karakas": ["Jupiter", "Venus", "Mercury", "Rahu"],
        "subject": "outside money — a loan, investment, or funding",
    },
    "relationship_entry": {
        "polarity": "gain", "varga": "d9",
        "houses": [7, 5, 11],
        "house_meaning": {7: "partnership and marriage", 5: "romance and the heart",
                          11: "the desire being fulfilled"},
        "karakas": ["Venus", "Jupiter"],
        "subject": "a significant person entering your life",
    },
    "separation": {
        "polarity": "risk", "varga": "d9",
        "houses": [7, 6, 8, 12],
        "house_meaning": {7: "the partnership itself", 6: "conflict and discord",
                          8: "upheaval and rupture", 12: "distance, loss, separate beds"},
        "karakas": ["Venus", "Moon"],
        "subject": "strain or separation in a partnership",
    },
    "health": {
        "polarity": "risk", "varga": "d9",
        "houses": [1, 6, 8, 12],
        "house_meaning": {1: "the body and vitality", 6: "illness and daily strain",
                          8: "chronic issues and procedures", 12: "hospitalisation and depletion"},
        "karakas": ["Sun", "Moon", "Mars", "Saturn"],
        "subject": "your health and vitality",
    },
}
# question routing → canonical concern
_ALIASES = {
    "funding": "funding", "loan": "funding", "investment": "funding", "capital": "funding",
    "love": "relationship_entry", "relationship": "relationship_entry",
    "marriage": "relationship_entry", "partner": "relationship_entry",
    "divorce": "separation", "separation": "separation", "breakup": "separation",
    "health": "health", "illness": "health", "disease": "health",
}


def _dignity(planet, sign):
    if _EXALT.get(planet) == sign:
        return 2.0, "exalted"
    if sign in _OWN.get(planet, set()):
        return 1.0, "in its own sign"
    if _DEBIL.get(planet) == sign:
        return -2.0, "debilitated"
    return 0.0, None


def _current_dasha_lords(dashas: dict) -> set:
    """Vimśottarī MD + AD lords active today (plus whatever Chara/Yoginī lords
    the payload exposes) — the 'is it lit now' set."""
    out = set()
    today = date.today().isoformat()
    for sysname in ("vimsottari", "vimshottari", "chara", "yogini"):
        periods = (dashas or {}).get(sysname) or []
        for p in periods if isinstance(periods, list) else []:
            if not isinstance(p, dict):
                continue
            lord = p.get("lord_or_sign") or p.get("planet_or_sign") or p.get("lord")
            s = str(p.get("start_date") or p.get("start") or "")[:10]
            e = str(p.get("end_date") or p.get("end") or "")[:10]
            if lord and s and e and s <= today <= e:
                out.add(str(lord).title())
    return out


def _planet_in_varga(chart_data: dict, varga: str, planet: str) -> Optional[str]:
    v = ((chart_data.get("divisional_charts") or {}).get(varga) or {})
    pv = (v.get("planets") or {}).get(planet)
    return pv.get("sign") if isinstance(pv, dict) else None


def analyze_concern(concern: str, chart_data: dict, dashas: dict) -> dict:
    """{available, verdict, score, drivers[], d9_confirms, dasha_active[],
    houses[], subject, narration_facts}. Never raises."""
    try:
        concern = _ALIASES.get((concern or "").lower(), (concern or "").lower())
        spec = CONCERN_SPEC.get(concern)
        cd = chart_data if isinstance(chart_data, dict) else {}
        planets = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign")
        if not spec or not planets or not lagna:
            return {"available": False}

        houses = spec["houses"]
        # significators = lords of the concern houses + karakas + planets sitting in them
        house_signs = {h: _sign_n_from(lagna, h) for h in houses}
        house_lords = {h: SIGN_LORD.get(house_signs[h]) for h in houses}
        in_house = {h: [p for p, v in planets.items()
                        if isinstance(v, dict) and v.get("house") == h] for h in houses}

        is_risk = spec["polarity"] == "risk"
        sig = {}   # planet -> {score, why[]}
        relief = 0.0
        def add(p, s, why):
            if not p:
                return
            d = sig.setdefault(p, {"score": 0.0, "why": []})
            d["score"] += s
            d["why"].append(why)

        cur = _current_dasha_lords(dashas)
        dasha_active = []

        # score each house's lord + occupants. GAIN = strength raises the score;
        # RISK = AFFLICTION raises it (malefics/debilitation), benefics give relief
        # so a healthy chart doesn't read 'elevated'.
        for h in houses:
            lord = house_lords[h]
            v = planets.get(lord) or {}
            dig, digword = _dignity(lord, v.get("sign"))
            note = f"rules your {_ord(h)} house ({spec['house_meaning'][h]})" + (f", {digword}" if digword else "")
            if is_risk:
                # debilitated/weak lord = affliction; dignified lord = relief
                if dig < 0:
                    add(lord, 1.0 - dig, note)          # debil (-2) -> +3
                elif dig > 0:
                    relief += 1.0
                else:
                    add(lord, 0.4, note)
            else:
                add(lord, 1.0 + dig, note)
            if lord in cur and lord not in dasha_active:
                # a running period lights the theme; for RISK only a malefic/weak
                # lord elevates it, a benefic/strong lord is protective.
                if not is_risk or dig < 0 or lord in _MALEFICS:
                    add(lord, 1.5, "and its period is running now")
                    dasha_active.append(lord)
                else:
                    relief += 0.5
            for p in in_house[h]:
                pv = planets.get(p) or {}
                pdig, pword = _dignity(p, pv.get("sign"))
                if is_risk:
                    if p in _MALEFICS:
                        add(p, 1.2 + max(0, -pdig), f"a hard planet sits in your {_ord(h)} house" + (f", {pword}" if pword else ""))
                    else:
                        relief += 0.7      # a benefic here softens it
                else:
                    add(p, 0.8 + max(0, pdig), f"sits in your {_ord(h)} house" + (f", {pword}" if pword else ""))

        # karakas
        for k in spec["karakas"]:
            kv = planets.get(k) or {}
            kdig, kword = _dignity(k, kv.get("sign"))
            if is_risk:
                if kdig < 0:
                    add(k, 0.8 - kdig, f"the natural significator is weak here" + (f", {kword}" if kword else ""))
            else:
                add(k, 0.6 + kdig, "is a natural significator here" + (f", {kword}" if kword else ""))
            if k in cur and k not in dasha_active and (not is_risk or kdig < 0 or k in _MALEFICS):
                add(k, 1.0, "and its period is running now")
                dasha_active.append(k)

        # D-9 confirmation — is the PRIMARY significator (first house's lord)
        # also dignified / not debilitated in the navamsa?
        d9_confirms = False
        primary = house_lords[houses[0]]
        d9_sign = _planet_in_varga(cd, spec["varga"], primary)
        if d9_sign:
            d9dig, _ = _dignity(primary, d9_sign)
            d9_confirms = d9dig >= 0

        # aggregate — RISK subtracts the benefic relief so a protected chart
        # reads calm, not "elevated".
        total = sum(d["score"] for d in sig.values())
        if is_risk:
            total = max(0.0, total - relief)
        drivers = sorted(({"planet": p, "score": round(d["score"], 2), "why": d["why"]}
                          for p, d in sig.items()), key=lambda x: x["score"], reverse=True)

        lit = bool(dasha_active)
        if not is_risk:
            if total >= 6 and lit and d9_confirms:
                verdict = "well supported"
            elif total >= 4 and (lit or d9_confirms):
                verdict = "supported, conditionally"
            else:
                verdict = "not strongly indicated right now"
        else:  # risk — only elevated on genuine affliction that's also lit
            if total >= 7 and lit:
                verdict = "elevated — worth active care"
            elif total >= 5 and lit:
                verdict = "worth watching"
            elif total >= 4:
                verdict = "a minor theme, not pressing"
            else:
                verdict = "not indicated right now — steady"

        facts = _facts_block(concern, spec, verdict, drivers, d9_confirms,
                             dasha_active, house_lords, in_house)
        return {"available": True, "concern": concern, "verdict": verdict,
                "score": round(total, 2), "polarity": spec["polarity"],
                "drivers": drivers[:5], "d9_confirms": d9_confirms,
                "dasha_active": dasha_active, "houses": houses,
                "subject": spec["subject"], "narration_facts": facts}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def _ord(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _facts_block(concern, spec, verdict, drivers, d9, dasha_active, lords, in_house):
    top = "; ".join(f"{d['planet']} ({', '.join(d['why'][:2])})" for d in drivers[:3])
    pol = spec["polarity"]
    lit = (", and it is active in the current planetary period"
           if dasha_active else ", but no active period is lighting it up yet")
    d9line = (" The navamsa (deeper chart) confirms this." if d9
              else " The navamsa is lukewarm on it, so treat it as partial.")
    frame = ("whether " + spec["subject"] + " is supported"
             if pol == "gain" else "whether " + spec["subject"] + " is a live risk")
    return (
        f"CONCERN ANALYSIS — the reader is asking about {frame}. This is computed "
        f"DETERMINISTICALLY from the houses that own this theme "
        f"({', '.join(spec['house_meaning'].values())}), their lords, the natural "
        f"significators, the navamsa, and the running dasha. You MUST answer from "
        f"THIS analysis — do not invent.\n"
        f"VERDICT: {verdict}{lit}.{d9line}\n"
        f"KEY SIGNIFICATORS: {top}.\n"
        "Lead with the verdict in plain words (for funding: say clearly whether "
        "OUTSIDE money — a loan, investment, or funding — is supported and why, in "
        "terms of gains/other-people's-money/debt; for a relationship: whether a "
        "real person can enter and how it forms; for separation/health: name it as "
        "a risk to manage, never a certainty, and stay supportive). Close with one "
        "concrete next step and, if a timing window was given above, cite it. "
        "Plain language only — never name a planet, house number, or 'navamsa'.")


def analyze_funding(chart_data, dashas):        return analyze_concern("funding", chart_data, dashas)
def analyze_relationship_entry(chart_data, dashas): return analyze_concern("relationship_entry", chart_data, dashas)
def analyze_separation(chart_data, dashas):     return analyze_concern("separation", chart_data, dashas)
def analyze_health(chart_data, dashas):         return analyze_concern("health", chart_data, dashas)
