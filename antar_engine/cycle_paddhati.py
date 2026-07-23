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


def cycle_reading(chart: dict, md: str, ad: str, pd: str,
                  chara_sign: Optional[str] = None,
                  transit_hits: Optional[Dict[str, str]] = None) -> Dict:
    """Read the running period through all four systems and report agreement."""
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

    return {
        "available": True,
        "verdict": verdict,
        "primary_house": primary,
        "primary_houses": leaders,
        "primary_house_meaning": HOUSE_MEANING.get(primary or 0, ""),
        "chara_sign": chara_sign,
        "chara_house": chara_house,
        "agreement": agreement,
        "layers": layers,
        "houses_lit": {str(k): round(v, 2) for k, v in ranked[:5]},
    }
