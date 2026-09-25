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

STATUS — v1, UNTUNED (2026-09-05): the METHOD (significator convergence,
dignity, D-9 confirmation, dasha activation) is sound and the computation is
deterministic, but the significator SETS above are v1 — classical defaults built
on d10_career's tables (which carry the same "starting point, not a final word"
caveat). They have NOT yet been validated against real dated outcomes. Treat the
output as a grounded first pass, not a proven mapping; refine the sets against
real charts before presenting any single concern verdict as authoritative.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from antar_engine.d10_career import (SIGNS, SIGN_LORD, _EXALT, _OWN,
                                     _sign_n_from, era_weight)

_DEBIL = {p: SIGNS[(SIGNS.index(s) + 6) % 12] for p, s in _EXALT.items()}
_DUSTHANA = {6, 8, 12}
_MALEFICS = {"Mars", "Saturn", "Rahu", "Ketu", "Sun"}

# concern → spec. polarity: "gain" (is the good thing supported?) or
# "risk" (is the bad thing elevated?). houses ordered by importance.
CONCERN_SPEC = {
    "income": {
        "polarity": "gain", "varga": "d9",
        "houses": [11, 2, 10, 6],
        "house_meaning": {11: "gains and what flows in", 2: "your earnings and savings",
                          10: "your livelihood and work income",
                          6: "recurring costs and debt that drag on cash flow"},
        "karakas": ["Jupiter", "Mercury", "Venus"],
        # [precision 2026-09-24] Jupiter is THE wealth significator (dhana karaka);
        # Mercury/Venus are secondary. A running PRIMARY karaka can light the domain;
        # a running secondary one only supports (see the karaka loop) — so income
        # doesn't read actively "well supported" off a minor wealth karaka alone.
        "primary_karakas": ["Jupiter"],
        "subject": "your income and cash flow",
    },
    "funding": {
        "polarity": "gain", "varga": "d9",
        "houses": [8, 11, 6, 2],
        "house_meaning": {8: "other people's money — loans, investment, funding",
                          11: "gains and what comes in", 6: "loans and debt taken on",
                          2: "your own capital"},
        "karakas": ["Jupiter", "Venus", "Mercury", "Rahu"],
        # Jupiter (benefactor/wealth) and Rahu (leverage, foreign/unconventional
        # capital) are the funding-specific significators; Venus/Mercury secondary.
        "primary_karakas": ["Jupiter", "Rahu"],
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
    "income": "income", "wealth": "income", "earnings": "income", "salary": "income",
    "cashflow": "income", "revenue": "income", "money": "income",
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


def _vim_active_lords(dashas: dict) -> set:
    """Vimśottarī MD+AD+PD lords active today — the PRIMARY 'period running now'
    set. [precision 2026-09-24] Kept SEPARATE from _current_dasha_lords (which
    also folds in Yoginī/chara), so a secondary-system lord can never claim the
    primary Vimśottarī 'its period is running now' credit — the bug where Yoginī-
    Mars was credited as the running period while the real MD (Rahu) was not."""
    out = set()
    today = date.today().isoformat()
    for sysname in ("vimsottari", "vimshottari"):
        for p in (dashas or {}).get(sysname) or []:
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


def analyze_concern(concern: str, chart_data: dict, dashas: dict,
                    intent: str = "state") -> dict:
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
        # [precision 2026-09-24] The spec's `houses` are ordered by importance, so
        # the first two are this domain's PRIMARY significator houses; the rest are
        # supporting/shared. This matters because the 11th (labha) sits in the
        # income, funding AND relationship_entry sets — a running planet merely
        # OCCUPYING that shared house must not light every gain-domain to
        # "well supported" off the same activator (the money-read bleed).
        primary_houses = set(houses[:2])
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
        # [precision 2026-09-24] the "period running now" credit is VIMŚOTTARĪ-only
        # (see _vim_active_lords): a Yoginī/chara lord must not be credited as the
        # running period, and the actual MD must be — even when it only OCCUPIES a
        # concern house (e.g. Rahu-in-11th, the current MD, is the primary income
        # activator but is a house-occupant, not a house-lord).
        vim_cur = _vim_active_lords(dashas)
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
            if lord in vim_cur and lord not in dasha_active:
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
                # [precision 2026-09-24] the running Vimśottarī MD/AD occupying a
                # concern house is a PRIMARY activator (Rahu-in-11th = the whole
                # gains chapter) — credit its running period here too, not only when
                # it happens to lord the house.
                if p in vim_cur and p not in dasha_active:
                    if not is_risk or pdig < 0 or p in _MALEFICS:
                        if h in primary_houses:
                            add(p, 1.5, "and its period is running now")
                            dasha_active.append(p)
                        else:
                            # [precision 2026-09-24] a running planet merely
                            # OCCUPYING a SHARED/tertiary house (the 11th, which
                            # every gain-domain contains) gives minor support only
                            # — it must NOT flip a domain to lit/"well supported" on
                            # a house that isn't this domain's primary significator.
                            add(p, 0.6, "and its period is running now (a supporting influence)")

        # karakas
        # [precision 2026-09-24] `primary_karakas` (defaults to ALL karakas, so
        # relationship/separation/health are unchanged — their primary karaka is
        # gender-dependent, e.g. Venus vs Jupiter for a spouse, so both stay full).
        # For the unambiguous wealth domains (income → Jupiter; funding → Jupiter/
        # Rahu) a running SECONDARY karaka only supports and does NOT set `lit`, so
        # the domain can't read actively "well supported" off a minor natural
        # significator alone when its own houses/lords aren't timing-active.
        primary_karakas = set(spec.get("primary_karakas", spec["karakas"]))
        for k in spec["karakas"]:
            kv = planets.get(k) or {}
            kdig, kword = _dignity(k, kv.get("sign"))
            if is_risk:
                if kdig < 0:
                    add(k, 0.8 - kdig, f"the natural significator is weak here" + (f", {kword}" if kword else ""))
            else:
                add(k, 0.6 + kdig, "is a natural significator here" + (f", {kword}" if kword else ""))
            if k in vim_cur and k not in dasha_active and (not is_risk or kdig < 0 or k in _MALEFICS):
                if k in primary_karakas:
                    add(k, 1.0, "and its period is running now")
                    dasha_active.append(k)
                else:
                    add(k, 0.5, "and its period is running now (a supporting natural significator)")

        # D-9 confirmation — is the PRIMARY significator (first house's lord)
        # also dignified / not debilitated in the navamsa?
        d9_confirms = False
        primary = house_lords[houses[0]]
        d9_sign = _planet_in_varga(cd, spec["varga"], primary)
        if d9_sign:
            d9dig, _ = _dignity(primary, d9_sign)
            d9_confirms = d9dig >= 0

        # [era-weighting] nudge significators by the present-age weight (Rahu/
        # Mercury up, Jupiter/Ketu down) — same lever as the career engine.
        for p in list(sig.keys()):
            sig[p]["score"] *= era_weight(p)

        # [node-affliction] a NODE (esp. Ketu) in a MONEY house (2 wealth / 11
        # gains / 8 other-people's-money) destabilizes it — gains come but don't
        # hold. Ketu-in-11th is the classic bankruptcy signature (Shashi). The
        # risk peaks when that node's dasha runs.
        # Ketu in a money house (2/11/8) dissolves gains — the real instability
        # (Ketu-in-11th = Shashi's bankruptcy). Rahu in the 11th is the OPPOSITE
        # — a classic gains asset (no warning); Rahu only warns in 2/8 (inflation
        # / debt volatility).
        node_warn = None
        if not is_risk:
            for h in [x for x in houses if x in (2, 11, 8)]:
                occ = in_house.get(h, [])
                if "Ketu" in occ:
                    node_warn = {"node": "Ketu", "house": h, "lit": "Ketu" in vim_cur,
                        "text": (f"Ketu sits in your {_ord(h)} house of "
                                 f"{spec['house_meaning'].get(h,'gains')} — gains can arrive "
                                 "suddenly but DON'T HOLD; there is a real risk of loss or "
                                 "reversal here, sharpest when its long period runs")}
                    break
                if "Rahu" in occ and h in (2, 8):
                    node_warn = {"node": "Rahu", "house": h, "lit": "Rahu" in vim_cur,
                        "text": (f"Rahu sits in your {_ord(h)} house of "
                                 f"{spec['house_meaning'].get(h,'wealth')} — gains here are "
                                 "volatile (inflation then reversal, easy over-reach); protect "
                                 "against sudden loss in its period")}
                    break

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
            # a node in the money house overrides toward instability, not denial —
            # the gains exist but are fragile; if its period is running, it's acute.
            if node_warn:
                verdict = ("supported but UNSTABLE — real loss/reversal risk right now, "
                           "protect capital" if node_warn["lit"]
                           else verdict + " — but UNSTABLE: gains here can reverse, protect against loss")
        else:  # risk — only elevated on genuine affliction that's also lit
            if total >= 7 and lit:
                verdict = "elevated — worth active care"
            elif total >= 5 and lit:
                verdict = "worth watching"
            elif total >= 4:
                verdict = "a minor theme, not pressing"
            else:
                verdict = "not indicated right now — steady"

        # [risk-twin differentiator 2026-09-24] separation [7,6,8,12] and health
        # [1,6,8,12] SHARE the 6/8/12 strain axis (disease+discord, chronic+rupture,
        # depletion+separate-beds) and legitimately co-elevate when it's lit. To keep
        # the two reads DISTINCT, tell the model whether THIS domain's own core is
        # independently hit — its unique anchor house (7th=partnership / 1st=body)
        # OR a significator unique to it (Venus for partnership; Sun/Mars/Saturn for
        # the body — Moon is shared, so it can't distinguish them) — vs. the pressure
        # being only the shared axis. Only when the domain is actually active.
        anchor_note = ""
        if is_risk and (dasha_active or total >= 5):
            anchor_h = houses[0]
            anchor_label = spec["house_meaning"][anchor_h]
            own_hit = any(p in _MALEFICS for p in in_house.get(anchor_h, []))
            _al = house_lords.get(anchor_h)
            if not own_hit and _dignity(_al, (planets.get(_al) or {}).get("sign"))[0] < 0:
                own_hit = True
            if not own_hit:
                for _k in spec["karakas"]:
                    if _k == "Moon":          # shared by both risk domains — can't distinguish
                        continue
                    if _dignity(_k, (planets.get(_k) or {}).get("sign"))[0] < 0:
                        own_hit = True
                        break
            if own_hit:
                anchor_note = (f"\nWHAT'S SPECIFIC TO THIS AREA: {anchor_label} is itself "
                               "directly involved — this is not merely a shared life-strain "
                               "season; say the core of THIS area is under real pressure.")
            else:
                anchor_note = (f"\nWHAT'S SPECIFIC TO THIS AREA: {anchor_label} is NOT "
                               "independently flagged — the pressure is coming from the shared "
                               "strain axis (daily friction, upheaval, depletion) that brushes "
                               "several life-areas at once. Frame this as a hard general season "
                               "touching this area, NOT this area's own core being singled out, "
                               "so the read stays distinct from a neighbouring one.")

        facts = _facts_block(concern, spec, verdict, drivers, d9_confirms,
                             dasha_active, house_lords, in_house, intent, node_warn,
                             anchor_note)
        return {"available": True, "concern": concern, "verdict": verdict,
                "score": round(total, 2), "polarity": spec["polarity"],
                "drivers": drivers[:5], "d9_confirms": d9_confirms,
                "dasha_active": dasha_active, "houses": houses,
                "subject": spec["subject"], "narration_facts": facts}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def _ord(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


# how the answer should LEAD, by question intent (the interrogative).
_INTENT_LEAD = {
    "state": "The reader is asking HOW THINGS ARE — lead with WHERE THEY ARE RIGHT "
             "NOW on {subj}: the current stretch, what's active, what's strong vs "
             "resisting. Then a short outlook. Present-tense, situational.",
    "timing": "The reader is asking WHEN — lead with the TIMING: when {subj} opens, "
              "turns, or resolves (cite the window given above; give a weeks/months "
              "horizon), then one line of why.",
    "channel": "The reader is asking HOW it will come — lead with the CHANNEL / MEANS: "
               "through which parts of life {subj} arrives (e.g. through your network, "
               "a mentor or senior, shared deals, your own effort, family) — read this "
               "from the significators and houses above. Then the outlook.",
    "cause": "The reader is asking WHY — lead with the CAUSE: what in the current "
             "period is driving {subj} (the key significator's condition and the "
             "house it touches), in plain everyday terms. Then what to do about it.",
    "outcome": "The reader is asking WHAT WILL HAPPEN — lead with the likely OUTCOME "
               "of {subj} as a forecast (the verdict framed forward), then the window "
               "and one concrete move.",
}


def _facts_block(concern, spec, verdict, drivers, d9, dasha_active, lords, in_house,
                 intent="state", node_warn=None, anchor_note=""):
    top = "; ".join(f"{d['planet']} ({', '.join(d['why'][:2])})" for d in drivers[:3])
    pol = spec["polarity"]
    intent_lead = _INTENT_LEAD.get(intent, _INTENT_LEAD["state"]).format(subj=spec["subject"])
    node_line = (f"\nCRITICAL INSTABILITY: {node_warn['text']} — you MUST surface this "
                 "loss/reversal risk in the answer (name it as a real risk to guard "
                 "against, not a certainty)." if node_warn else "")
    lit = (", and it is active in the current planetary period"
           if dasha_active else ", but no active period is lighting it up yet")
    d9line = (" The navamsa (deeper chart) confirms this." if d9
              else " The navamsa is lukewarm on it, so treat it as partial.")
    frame = ("whether " + spec["subject"] + " is supported"
             if pol == "gain" else "whether " + spec["subject"] + " is a live risk")

    # [funding-timing 2026-09-23] A "when funding / when money" question was
    # answering vaguely because the significator block carries no dated WHEN — the
    # timing lives in a SEPARATE convergence/transit block in the same context,
    # and nothing told the model to fuse them. For a money-GAIN concern asked as a
    # timing question, demand the explicit three-layer structure a KP/Jyotish
    # reader gives: GATE (running period) + TRIGGER (the dated transit window) +
    # CHANNEL (which money house it flows through). This is what makes the answer
    # land as direct as a human astrologer's, instead of "money is supported".
    timing_structure = ""
    if concern in ("funding", "income") and intent == "timing":
        _gate = ("OPEN NOW — a running life-period is already active on this theme, "
                 "so lead by saying the door is open and the work is to be in-market "
                 "in the trigger window"
                 if dasha_active else
                 "not fully open yet — say the earliest it opens (from the window "
                 "provided) rather than implying it is live today")
        timing_structure = (
            "\nTIMING — ANSWER IN THIS ORDER (plain language, be direct and dated):\n"
            f"1) THE GATE: {_gate}.\n"
            "2) THE TRIGGER: the specific months it actually lands — cite the dated "
            "window given elsewhere in this context (a slow, supportive influence "
            "crossing the money houses is the trigger on top of the open period). "
            "Give a real quarter / months horizon (e.g. 'strongest from <month> "
            "through <month>'), never 'sometime' and never 'not indicated'.\n"
            "3) THE CHANNEL: HOW it arrives — through gains and your network, through "
            "outside capital (an investor / a loan), or from your own reserves — read "
            "from the significators above.\n"
            "IMPORTANT: the chart times the MONEY, not which company/venture — do "
            "NOT name or pick a specific business. If the door is open, say so "
            "plainly and give the window; do not hedge it into a non-answer.")
    return (
        f"CONCERN ANALYSIS — the reader is asking about {frame}. This is computed "
        f"DETERMINISTICALLY from the houses that own this theme "
        f"({', '.join(spec['house_meaning'].values())}), their lords, the natural "
        f"significators, the navamsa, and the running dasha. You MUST answer from "
        f"THIS analysis — do not invent.\n"
        f"VERDICT: {verdict}{lit}.{d9line}{node_line}{anchor_note}{timing_structure}\n"
        f"KEY SIGNIFICATORS: {top}.\n"
        f"STAY STRICTLY ON ONE TOPIC: {spec['subject']}. Do NOT bring in any other "
        "life area — a health answer must NEVER mention money, loans, or funding; a "
        "funding answer must NEVER mention health or relationships; a relationship "
        "answer must NEVER mention career or money. Answer ONLY what was asked. "
        "Ignore any other chart data above that is off this topic.\n"
        f"HOW TO ANSWER: {intent_lead} This is a PERIOD question — give a weeks/"
        "months horizon, NEVER a same-day 'tonight / before HH:MM' answer. "
        "Domain framing (for funding: OUTSIDE money — loan/investment/funding, in "
        "terms of gains/other-people's-money/debt; for a relationship: whether a "
        "real person can enter and how; for separation/health: a risk to MANAGE, "
        "never a certainty, stay supportive). Close with one concrete next step. "
        "Plain language only — never name a planet, house number, or 'navamsa'.")


def analyze_funding(chart_data, dashas):        return analyze_concern("funding", chart_data, dashas)
def analyze_relationship_entry(chart_data, dashas): return analyze_concern("relationship_entry", chart_data, dashas)
def analyze_separation(chart_data, dashas):     return analyze_concern("separation", chart_data, dashas)
def analyze_health(chart_data, dashas):         return analyze_concern("health", chart_data, dashas)
