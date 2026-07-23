"""
antar_engine/cycle_paddhati.py
The current period, read through several systems at once.     2026-07-22

An audit of the Current Cycle surface found it reading the Vimshottari lords,
the chara dasha sign and transits — and NOT ONE of the fifteen divisional charts
stored on every record. That is the layer classical practice uses to answer the
question the cycle tab exists for: not "which period is running" but "will this
period actually deliver".

The four readings combined here, and what each is for:

  1. VIMSHOTTARI (mahadasha / antardasha / pratyantardasha)
     Which lords are running, and what houses they own and occupy. This says
     WHAT the period is about.

  2. VARGA DIGNITY of those same lords — D-9 above all
     A dasha lord gives according to its strength in the divisionals. The same
     Mars period is a different life depending on whether Mars is vargottama or
     debilitated in navamsa. D-9 says whether the promise materialises; D-10
     says what it does to the career specifically. This says WHETHER it delivers.

  3. CHARA DASHA (Jaimini)
     A sign-based period. Counted from the lagna it names the AREA OF LIFE the
     stretch is being lived from — the 5th is past credit and creativity, the
     7th partnership, the 10th standing. This says WHERE it happens.

  4. TRANSITS to the running lords
     Whether the sky is currently supporting or obstructing the lords that own
     the period. This says WHEN inside the period.

CONVICTION COMES FROM AGREEMENT, NOT FROM VOLUME. When two independent systems
point at the same house, that is worth saying loudly. When they disagree, the
honest output is that the period is mixed — not an averaged number that hides
the disagreement. A reading that always sounds certain is not reading anything.
"""

from typing import Dict, List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

EXALTED = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
           "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
           "Saturn": "Libra", "Rahu": "Taurus", "Ketu": "Scorpio"}
DEBILITATED = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
               "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
               "Saturn": "Aries", "Rahu": "Scorpio", "Ketu": "Taurus"}
OWN = {"Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
       "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
       "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"]}

HOUSE_MEANING = {
    1: "yourself, your health, how you come across",
    2: "money in hand, family, what you say",
    3: "your own effort, courage, communication",
    4: "home, mother, property, peace of mind",
    5: "children, creativity, learning, past credit, speculation",
    6: "work, service, competitors, debt, health routine",
    7: "partner, clients, deals",
    8: "sudden change, other people's money, deep research",
    9: "luck, father, teachers, belief, long journeys",
    10: "career, reputation, public standing",
    11: "income, gains, friends, networks",
    12: "expense, foreign places, rest, letting go",
}

# The seven Chara karakas, and what each governs when the chart is re-read from
# the running chara-dasha sign as a temporary lagna. This is the Jaimini reading
# proper: the dasha sign becomes the 1st house and the karakas are read by the
# house they fall in FROM it — not the natal lagna. AmK (career) landing in the
# 10th from the chara sign is a professional-peak signal that the Vimshottari
# lords may say nothing about, which is exactly why it is a second opinion.
KARAKA_ROLE = {
    "AK":  "your own direction and what the stretch is really about",
    "AmK": "career and profession",
    "BK":  "learning, siblings, and the people around you",
    "MK":  "home, mother, and property",
    "PK":  "children, creativity, and past credit",
    "GK":  "obstacles, health, and what has to be fought",
    "DK":  "partnership and the people you bind to",
}
# Which houses from the chara sign a karaka is 'lit' in — kendras and trikonas
# are where a karaka's affairs come forward; the 6/8/12 are where they are
# tested. Kept classical and small on purpose.
_KARAKA_STRONG = {1, 4, 5, 7, 9, 10}
_KARAKA_TESTED = {6, 8, 12}

# The four slow movers are the only transits whose window matches a dasha
# sub-period. Sun/Moon/Mercury/Venus/Mars change too fast to define WHEN inside
# a period that runs months to years. Each carries a direction, not just a hit.
_SLOW_TRANSITS = {
    "Jupiter": ("supports and expands", +1.0),
    "Saturn":  ("presses, slows, and consolidates", -1.0),
    "Rahu":    ("amplifies and destabilises", -0.4),
    "Ketu":    ("dissolves and detaches", -0.4),
}


def _ord(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _lagna_index(chart: dict) -> int:
    lg = (chart or {}).get("lagna") or {}
    i = lg.get("sign_index")
    return i if isinstance(i, int) and 0 <= i <= 11 else 0


def _house_of_sign(chart: dict, sign: str) -> Optional[int]:
    """Which house a SIGN occupies, counted from the lagna (whole-sign)."""
    if sign not in SIGNS:
        return None
    return ((SIGNS.index(sign) - _lagna_index(chart)) % 12) + 1


def _houses_ruled(chart: dict, planet: str) -> List[int]:
    li = _lagna_index(chart)
    return [h for h in range(1, 13) if SIGN_LORD[(li + h - 1) % 12] == planet]


def _varga_sign(chart: dict, planet: str, varga: str) -> Optional[str]:
    dc = (chart or {}).get("divisional_charts") or {}
    return ((dc.get(varga) or {}).get("planets") or {}).get(planet, {}).get("sign")


def varga_dignity(chart: dict, planet: str) -> Dict:
    """Does this lord actually deliver? D-1 vs D-9, plus D-10 for career.

    Vargottama — the same sign in D-1 and D-9 — is the strongest single
    statement the divisionals make about a planet. It means the promise holds
    all the way down: what the birth chart offers, the navamsa confirms.
    """
    d1 = ((chart or {}).get("planets") or {}).get(planet, {}).get("sign")
    d9 = _varga_sign(chart, planet, "d9")
    d10 = _varga_sign(chart, planet, "d10")

    score, notes = 0.0, []
    vargottama = bool(d1 and d9 and d1 == d9)
    if vargottama:
        score += 2.0
        notes.append(f"{planet} is vargottama — the same sign in the birth chart "
                     f"and the navamsa. What it promises, it delivers.")

    if d9 == EXALTED.get(planet):
        score += 1.5
        notes.append(f"{planet} is exalted in the navamsa — this period gives "
                     f"more than the birth chart alone suggests.")
    elif d9 in OWN.get(planet, []):
        score += 1.0
        notes.append(f"{planet} is in its own sign in the navamsa — it holds its "
                     f"own ground through this period.")
    elif d9 == DEBILITATED.get(planet):
        score -= 1.5
        notes.append(f"{planet} is debilitated in the navamsa — the period tends "
                     f"to promise more than it hands over. Expect the result to "
                     f"arrive smaller or later than it looks.")

    if d10 == EXALTED.get(planet):
        score += 0.5
        notes.append(f"{planet} is exalted in the career chart — this period "
                     f"lifts professional standing specifically.")
    elif d10 == DEBILITATED.get(planet):
        score -= 0.5
        notes.append(f"{planet} is debilitated in the career chart — work is the "
                     f"area that has to be worked hardest through this period.")

    band = "delivers" if score >= 1.5 else "holds" if score >= 0 else "underdelivers"
    return {"planet": planet, "d1": d1, "d9": d9, "d10": d10,
            "vargottama": vargottama, "score": round(score, 2),
            "band": band, "notes": notes}


def _sign_index_of_planet(chart: dict, planet: str) -> Optional[int]:
    d = ((chart or {}).get("planets") or {}).get(planet) or {}
    si = d.get("sign_index")
    if isinstance(si, int):
        return si % 12
    s = d.get("sign")
    return SIGNS.index(s) if s in SIGNS else None


def transit_pressure(chart: dict, lords: List[str],
                     transits: Optional[List[dict]]) -> Dict:
    """WHEN inside the period — which slow transits are on the running lords now.

    Classical gochara restricted to the four planets whose transit lasts long
    enough to shape a dasha sub-period. A transit counts when the slow planet is
    (a) in the same sign as a running lord's natal position — sitting on the lord
    — or (b) moving through a house that lord rules or occupies. Jupiter lifts,
    Saturn consolidates and delays, the nodes destabilise. This does not change
    WHAT the period is about; it says whether the sky is behind it right now.
    """
    if not transits:
        return {"available": False, "notes": [], "net": 0.0}
    tmap = {}
    for t in transits:
        p = t.get("planet")
        if p in _SLOW_TRANSITS and isinstance(t.get("current_house"), int):
            tmap[p] = {"sign": t.get("current_sign"),
                       "house": t.get("current_house")}
    notes, net = [], 0.0
    seen = set()
    for lord in lords:
        if not lord:
            continue
        lord_sign_idx = _sign_index_of_planet(chart, lord)
        lord_sign = SIGNS[lord_sign_idx] if lord_sign_idx is not None else None
        owns = set(_houses_ruled(chart, lord))
        sits = ((chart.get("planets") or {}).get(lord) or {}).get("house")
        if isinstance(sits, int):
            owns.add(sits)
        for tp, td in tmap.items():
            verb, weight = _SLOW_TRANSITS[tp]
            key = None
            if lord_sign and td["sign"] == lord_sign:
                key = (tp, lord, "on")
                if key not in seen:
                    notes.append(f"Transiting {tp} is sitting on your period lord "
                                 f"{lord} (both in {lord_sign}) — it {verb} what "
                                 f"{lord} is running right now.")
                    net += weight * 1.0
            elif td["house"] in owns:
                key = (tp, lord, "house")
                if key not in seen:
                    hm = HOUSE_MEANING.get(td["house"], "")
                    notes.append(f"Transiting {tp} is moving through your "
                                 f"{_ord(td['house'])} house ({hm}), which {lord} "
                                 f"governs this period — it {verb} that area now.")
                    net += weight * 0.6
            if key:
                seen.add(key)
    return {"available": bool(notes), "notes": notes, "net": round(net, 2)}


def chara_karaka_rotation(chara_sign: Optional[str],
                          karakas: Optional[Dict[str, int]]) -> Dict:
    """The Jaimini moving-lagna reading: chara sign becomes the 1st house.

    The user's own description of the layer — 'in the chara dasha the mahadasha
    becomes the lagna, and the AK, AmK all rotate'. Each karaka is read by the
    house it falls in counted FROM the chara sign, not the natal lagna. This is a
    genuinely independent opinion because it uses the Jaimini karaka scheme and
    the sign-based period, sharing no arithmetic with the Vimshottari house map.
    """
    if not chara_sign or chara_sign not in SIGNS or not karakas:
        return {"available": False, "findings": [], "lit_houses": []}
    base = SIGNS.index(chara_sign)
    findings, lit = [], []
    for k, role in KARAKA_ROLE.items():
        sidx = karakas.get(k)
        if not isinstance(sidx, int):
            continue
        house = ((sidx - base) % 12) + 1
        if house in _KARAKA_STRONG:
            findings.append(f"From your chara sign {chara_sign}, your {k} "
                            f"({role}) sits in the {_ord(house)} — this stretch "
                            f"brings {role} forward.")
            if k in ("AK", "AmK", "DK"):
                lit.append(house)
        elif house in _KARAKA_TESTED:
            findings.append(f"From your chara sign {chara_sign}, your {k} "
                            f"({role}) sits in the {_ord(house)} — {role} is the "
                            f"part of this stretch that gets tested.")
    return {"available": bool(findings), "findings": findings,
            "lit_houses": lit, "chara_sign": chara_sign}


def _handover_note(chart: dict, md: str, md_ends: Optional[str],
                   next_md: Optional[str]) -> Optional[str]:
    """The most important fact a cycle can carry: a mahadasha about to change.

    A mahadasha handover is the largest boundary in the vimshottari scheme — the
    incoming lord resets what the next stretch of life is about. Being weeks from
    one, especially into an 18-year Rahu or 19-year Saturn, dwarfs any sub-period
    detail, so it is surfaced above everything else rather than buried in a layer.
    """
    if not md_ends or not next_md:
        return None
    from datetime import date
    try:
        y, m, d = (int(x) for x in md_ends[:10].split("-"))
        days = (date(y, m, d) - date.today()).days
    except Exception:
        return None
    if not (0 <= days <= 120):
        return None
    incoming_houses = _houses_ruled(chart, next_md)
    incoming_where = ((chart.get("planets") or {}).get(next_md) or {}).get("house")
    where = (f" — it will run your {_ord(incoming_where)} house "
             f"({HOUSE_MEANING.get(incoming_where, '')})" if incoming_where else "")
    owns = (f", and rules your " + " and ".join(_ord(h) for h in incoming_houses)
            if incoming_houses else "")
    wk = max(1, round(days / 7))
    return (f"Your {md} mahadasha ends in about {wk} week{'s' if wk != 1 else ''} "
            f"({md_ends[:10]}), and your {next_md} mahadasha begins then{where}"
            f"{owns}. This is the largest turn in the whole cycle: the sub-periods "
            f"below belong to the {md} chapter that is closing, and the {next_md} "
            f"chapter rewrites what the coming years are about.")


def cycle_reading(chart: dict, md: str, ad: str, pd: str,
                  chara_sign: Optional[str] = None,
                  transits: Optional[List[dict]] = None,
                  karakas: Optional[Dict[str, int]] = None,
                  muntha: Optional[str] = None,
                  md_ends: Optional[str] = None,
                  next_md: Optional[str] = None) -> Dict:
    """Read the running period through every system at once and report agreement.

    Layers, each an independent opinion:
      Vimshottari MD/AD/PD lords + their varga dignity   — WHAT, and WHETHER
      Chara-dasha sign as house, and karaka rotation     — WHERE (Jaimini)
      Muntha (annual Tajika pointer)                     — WHERE, this year
      Slow transits on the running lords                 — WHEN, right now
    """
    if not chart or not chart.get("planets"):
        return {"available": False}

    lords = [("Mahadasha", md, 1.0), ("Antardasha", ad, 0.8),
             ("Pratyantardasha", pd, 0.5)]
    layers, houses_lit = [], {}

    for label, lord, weight in lords:
        if not lord:
            continue
        dig = varga_dignity(chart, lord)
        owns = _houses_ruled(chart, lord)
        sits = ((chart.get("planets") or {}).get(lord) or {}).get("house")
        for h in owns + ([sits] if isinstance(sits, int) else []):
            houses_lit[h] = houses_lit.get(h, 0.0) + weight
        layers.append({
            "level": label, "lord": lord, "rules": owns, "sits_in": sits,
            "dignity": dig,
        })

    # Chara dasha: the sign, read as a house from the lagna. This is the second
    # independent opinion — a different system entirely, not a restatement.
    chara_house = _house_of_sign(chart, chara_sign) if chara_sign else None
    if chara_house:
        houses_lit[chara_house] = houses_lit.get(chara_house, 0.0) + 1.0

    # Chara moving-lagna: the karakas re-read from the chara sign as 1st house.
    # A third independent voter — its lit houses (AK/AmK/DK) join the tally at a
    # lighter weight, since it speaks to karaka affairs rather than house rulership.
    rotation = chara_karaka_rotation(chara_sign, karakas)
    for h in rotation.get("lit_houses", []):
        houses_lit[h] = houses_lit.get(h, 0.0) + 0.5

    # Muntha: the annual Tajika pointer — the natal lagna advanced one sign per
    # year of life. It marks the house the YEAR is being lived from, and is the
    # only layer here that is specific to the current twelve months.
    muntha_house = _house_of_sign(chart, muntha) if muntha else None
    if muntha_house:
        houses_lit[muntha_house] = houses_lit.get(muntha_house, 0.0) + 0.7

    # Transits: the timing modifier. NOT a house-vote — it does not change what
    # the period is about, only whether the sky is behind it now.
    transit = transit_pressure(chart, [md, ad, pd], transits)

    ranked = sorted(houses_lit.items(), key=lambda kv: kv[1], reverse=True)
    # Ties are common and must not be resolved silently. On a live chart three
    # houses scored 1.5 apiece and the first in sort order was reported as "the"
    # primary house — which is a tie-break masquerading as a reading. Every house
    # at the top score is carried.
    top_score = ranked[0][1] if ranked else 0.0
    leaders = [h for h, v in ranked if v >= top_score - 1e-9]
    primary = leaders[0] if leaders else None

    # AGREEMENT is the thing worth reporting. Two independent systems pointing at
    # one house is a real statement; one system pointing anywhere is a guess.
    agreement = []
    if chara_house and chara_house in leaders:
        agreement.append(
            f"Two independent systems land on the same place: the Vimshottari "
            f"lords and the chara dasha sign {chara_sign} both weight house "
            f"{chara_house} — {HOUSE_MEANING.get(chara_house, '')}. When two "
            f"methods that share no arithmetic agree, that is the part of the "
            f"period to take seriously.")
    elif chara_house and primary:
        agreement.append(
            f"The two systems disagree, and that is information rather than a "
            f"problem. The running lords weight {HOUSE_MEANING.get(primary, '')}, "
            f"while the chara dasha sign {chara_sign} points at "
            f"{HOUSE_MEANING.get(chara_house, '')}. Expect the period to be split "
            f"between the two rather than clean.")

    # Muntha agreement — when the year's pointer lands on a house the period
    # lords already weight, the current twelve months concentrate the dasha.
    if muntha_house and muntha_house in leaders:
        agreement.append(
            f"This year's Muntha sits in your {_ord(muntha_house)} house "
            f"({HOUSE_MEANING.get(muntha_house, '')}), the same area the running "
            f"lords weight — so the annual chart concentrates the period into "
            f"these twelve months rather than spreading it thin.")

    if len(leaders) > 1:
        agreement.append(
            "This period does not have one centre of gravity — "
            + ", ".join(HOUSE_MEANING.get(h, str(h)) for h in leaders[:3])
            + " carry equal weight. A period pulling in several directions is a "
              "real thing; naming one of them would be a guess dressed as a reading.")

    delivering = [l for l in layers if l["dignity"]["band"] == "delivers"]
    weak = [l for l in layers if l["dignity"]["band"] == "underdelivers"]

    if delivering and not weak:
        verdict = "This period delivers what it promises."
    elif weak and not delivering:
        verdict = ("This period promises more than it hands over — the timing is "
                   "live but the result arrives smaller or later than it looks.")
    elif delivering and weak:
        verdict = ("Mixed: part of this period is solid and part of it is thinner "
                   "than it appears. The levels do not agree.")
    else:
        verdict = "This period holds steady — neither a lift nor a drag."

    # The transit line is the WHEN. Dignity says whether the period delivers at
    # all; transit says whether the sky is behind it in this window specifically.
    # They are different axes and are reported as such — a delivering period under
    # Saturn pressure is real, and so is a weak period Jupiter is currently lifting.
    if transit.get("available"):
        if transit["net"] >= 0.8:
            timing = ("Right now the slow transits are behind this period — the "
                      "window is open, act while it is.")
        elif transit["net"] <= -0.8:
            timing = ("Right now the slow transits are pressing on this period — "
                      "the promise holds, but this stretch asks for patience "
                      "rather than a push.")
        else:
            timing = ("The slow transits are mixed on this period right now — "
                      "neither a clear opening nor a clear block.")
    else:
        timing = ""

    handover = _handover_note(chart, md, md_ends, next_md)

    return {
        "available": True,
        "verdict": verdict,
        "timing": timing,
        "handover": handover,
        "primary_house": primary,
        "primary_houses": leaders,
        "primary_house_meaning": HOUSE_MEANING.get(primary or 0, ""),
        "chara_sign": chara_sign,
        "chara_house": chara_house,
        "chara_rotation": rotation.get("findings", []),
        "muntha_sign": muntha,
        "muntha_house": muntha_house,
        "transit": transit,
        "agreement": agreement,
        "layers": layers,
        "houses_lit": {str(k): round(v, 2) for k, v in ranked[:5]},
    }
