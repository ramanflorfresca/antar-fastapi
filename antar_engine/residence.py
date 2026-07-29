"""
antar_engine/residence.py

Deterministic CHANGE-OF-RESIDENCE (relocation) engine — the WHEN. Answers:
  • DISPOSITION — rooted (stays put) vs mobile vs foreign-inclined, from the 4th
    (home/roots) against the 12th/9th (distant/foreign) + Moon/Rahu + a movable
    lagna.
  • TIMING — when a move is likely, via the shared multi-system convergence with
    the Lal-Kitab varshphal weighted HEAVILY (owner: most accurate yearly).
  • NATURE — a new home nearby vs a distant/foreign relocation vs a settling-down,
    from which houses/planets drive the window.

NOTE: this is the WHEN, and is SEPARATE from astrocartography (the WHERE — the
relocation-chart recompute for a candidate location). Houses: 4 (home/roots/land/
vehicles), 12 (foreign/settling away/exit), 3 (short moves/initiative), 9 (long
journeys/foreign fortune). Karakas: Moon (home/change), Rahu (foreign/sudden),
Saturn (permanence/land), Venus (comfort/vehicles). LLM narrates only. v1.
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.relationships import _dig, _house_of, _in_house, _malefics_on, _benefics_on
from antar_engine.domain_timing import domain_convergence

_MOVABLE = {"Aries", "Cancer", "Libra", "Capricorn"}
_DUAL = {"Gemini", "Virgo", "Sagittarius", "Pisces"}

RESIDENCE_SPEC = {
    "noun": "a change of home",
    "houses": [4, 12, 3, 9],
    "activator_houses": [4, 12, 3],
    "karakas": ["Moon", "Rahu", "Saturn", "Venus"],
    "varsh_houses": [4, 12],
    "transit_grahas": ["Saturn", "Rahu", "Jupiter", "Ketu"],
    "transit_houses": [4, 12, 1],
    "malefic_varsh": False,     # ANY planet lighting the varshphal 4th/12th = a move that year
    "varsh_weight": 1.8,        # LK varshphal weighted heavily (owner directive)
    "min_score": 2.0,
}


def _residence_nature(chart_data, lords) -> list:
    """Domestic vs distant/foreign vs settling, from the activating lords."""
    cd = chart_data or {}
    d1 = cd.get("planets") or {}
    lagna = ((cd.get("lagna") or {}).get("sign"))
    if not lagna:
        return []
    fourth_lord = SIGN_LORD.get(_sign_n_from(lagna, 4))
    third_lord = SIGN_LORD.get(_sign_n_from(lagna, 3))
    ninth_lord = SIGN_LORD.get(_sign_n_from(lagna, 9))
    twelfth_lord = SIGN_LORD.get(_sign_n_from(lagna, 12))
    out, seen = [], set()

    def _push(t):
        if t and t not in seen:
            seen.add(t); out.append(t)

    for lord in lords:
        if not lord:
            continue
        h = _house_of(lord, d1)
        if lord in ("Rahu",) or lord in (twelfth_lord, ninth_lord) or h in (12, 9):
            _push("a move to a distant place or abroad")
        elif lord in (fourth_lord,) or lord == "Moon" or h == 4:
            _push("a new home, or a move within your region")
        elif lord == third_lord or h == 3:
            _push("a short-distance move, close by")
        if lord == "Saturn":
            _push("a settling-down into a more permanent base")
        if lord == "Venus":
            _push("an upgrade in comfort or a nicer home")
    return out[:2]


def analyze_residence(chart_data: dict) -> dict:
    """{available, disposition{}, factors{}, summary}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        d1 = cd.get("planets") or {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not d1 or not lagna:
            return {"available": False}

        fourth = _sign_n_from(lagna, 4)
        fourth_lord = SIGN_LORD.get(fourth)
        twelfth_lord = SIGN_LORD.get(_sign_n_from(lagna, 12))

        # rooted (strong, benefic 4th) vs mobile (afflicted 4th, Rahu/12th active,
        # movable lagna, Moon in a movable/dual sign)
        rooted, mobile, flags = 0.0, 0.0, []
        if _dig(fourth_lord, (d1.get(fourth_lord) or {}).get("sign"))[0] >= 0 and _benefics_on(d1, 4):
            rooted += 1.0; flags.append("a settled, well-supported home base")
        if _malefics_on(d1, 4):
            mobile += 0.8; flags.append("restlessness around the home (the 4th is stirred)")
        if _house_of(fourth_lord, d1) in (12, 9, 3, 8):
            mobile += 0.8; flags.append("the ruler of home sits in a house of movement/distance")
        if _house_of("Rahu", d1) in (4, 12):
            mobile += 0.8; flags.append("a strong pull toward the foreign/unconventional in home life")
        if lagna in _MOVABLE:
            mobile += 0.6; flags.append("a naturally mobile, movable rising sign")
        moon_sign = (d1.get("Moon") or {}).get("sign")
        if moon_sign in _MOVABLE or moon_sign in _DUAL:
            mobile += 0.4; flags.append("a changeable, travel-inclined mind")
        # foreign inclination — 4th↔12th link, or 12th lord tied to home
        foreign = (_house_of(fourth_lord, d1) == 12 or _house_of(twelfth_lord, d1) == 4
                   or _house_of("Rahu", d1) in (4, 12))

        if mobile - rooted >= 1.2:
            level = "inclined to relocate" + (" — often to distant/foreign places" if foreign else "")
        elif rooted - mobile >= 1.0:
            level = "rooted — you tend to stay put and put down deep roots"
        else:
            level = "balanced between roots and movement"
        disposition = {"rooted": round(rooted, 2), "mobile": round(mobile, 2),
                       "foreign": bool(foreign), "level": level, "flags": flags}

        factors = {"fourth_sign": fourth, "fourth_lord": fourth_lord,
                   "planets_in_4th": _in_house(d1, 4)}
        summary = f"Home disposition: {level}."
        return {"available": True, "disposition": disposition, "factors": factors,
                "summary": summary}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


def residence_timing(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                     today: Optional[str] = None) -> dict:
    """When a move is likely — multi-system convergence (varshphal-heavy). Returns
    {available, windows[], best, summary}."""
    res = domain_convergence(chart_data, dashas, RESIDENCE_SPEC, birth_date=birth_date, today=today)
    if not res.get("available"):
        return res
    for w in res.get("windows", []):
        parts = [x.strip() for x in w["label"].replace("–", "-").split("-")]
        w["nature"] = _residence_nature(chart_data, parts)
    best = res.get("best")
    if best:
        nat = best.get("nature") or []
        res["summary"] = (f"The most likely window for a move is around {best['start'][:7]} "
                          f"— {len(best['systems'])} systems agree"
                          + (f", pointing to {nat[0]}." if nat else "."))
        res["nature"] = nat
    else:
        res["summary"] = "No sharply-converging relocation window ahead — no structural move flagged."
        res["nature"] = []
    return res
