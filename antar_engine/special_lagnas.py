"""
antar_engine/special_lagnas.py
Which reference point a question should actually be read from.  2026-07-22

The birth ascendant is not the right origin for every question, and using it for
all of them is why readings blur together. Jaimini gives distinct reference
points, each answering a different kind of question:

    LAGNA           what you ARE — body, health, self
    ARUDHA LAGNA    what you SEEM — image, reputation, standing, maya
    UPAPADA LAGNA   the marriage — the spouse and the bond
    SRI LAGNA       where prosperity settles

The distinction that matters most in practice is lagna versus arudha. Someone
asking "will people respect this venture" is not asking about their body or
their vitality; they are asking about their image, which is the arudha. Reading
that from the ascendant answers a question they did not ask. Conversely a health
question read from the arudha would be nonsense — the arudha knows nothing about
the body.

The classical wealth indicator in Jaimini is A11, the 11th FROM the arudha, not
the 11th from the lagna. The 11th from the lagna is what you receive; A11 is
what the world can see you have. For a person asking whether a business will
make them money, both matter and they are not the same house.

For marriage, the 2nd from the Upapada is the classical seat of the marriage's
sustenance: malefics there are the standard indication of difficulty or
separation. That is a specific, falsifiable claim, and it is checked here
against the chart rather than asserted.

WHAT THIS MODULE WILL NOT DO. It does not predict divorce, wealth amounts or
dates. It selects the correct reference point for a question and reports what
sits there. Selection is the contribution; the interpretation stays with the
reading engine.
"""

from typing import Dict, List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

# Which reference each kind of question should be read from. A question can
# legitimately need more than one — "will my business make me money and will
# people take it seriously" is A11 and arudha together.
CONCERN_REFERENCE = {
    "reputation":  ["arudha"],
    "fame":        ["arudha"],
    "image":       ["arudha"],
    "status":      ["arudha"],
    "career":      ["lagna", "arudha"],
    "business":    ["arudha", "sri"],
    "startup":     ["arudha", "sri"],
    "job":         ["lagna"],
    "wealth":      ["sri", "arudha"],
    "money":       ["sri", "arudha"],
    "finance":     ["sri", "arudha"],
    "funding":     ["arudha", "sri"],
    "marriage":    ["upapada"],
    "spouse":      ["upapada"],
    "divorce":     ["upapada"],
    "relationship": ["upapada"],
    "health":      ["lagna"],
    "body":        ["lagna"],
    "general":     ["lagna", "arudha"],
}


def _lagna_index(chart: dict) -> int:
    lg = (chart or {}).get("lagna") or {}
    i = lg.get("sign_index")
    return i if isinstance(i, int) and 0 <= i <= 11 else 0


def _sign_index_of(chart: dict, planet: str) -> Optional[int]:
    d = ((chart or {}).get("planets") or {}).get(planet) or {}
    si = d.get("sign_index")
    if isinstance(si, int):
        return si % 12
    lon = d.get("longitude")
    return int(lon // 30) % 12 if isinstance(lon, (int, float)) else None


def _occupants_of_sign(chart: dict, sign_idx: int) -> List[str]:
    return [p for p in ((chart or {}).get("planets") or {})
            if _sign_index_of(chart, p) == sign_idx]


def _jaimini_planets(chart: dict):
    from antar_engine.jaimini_engine import Planet
    out = {}
    for p, d in ((chart or {}).get("planets") or {}).items():
        lon = d.get("longitude") if isinstance(d, dict) else None
        if isinstance(lon, (int, float)):
            out[p] = Planet(name=p, sign=int(lon // 30) % 12,
                            degree=float(lon), degree_in_sign=float(lon) % 30)
    return out


def all_references(chart: dict) -> Dict:
    """Every reference point this chart offers, with its house from the lagna."""
    li = _lagna_index(chart)
    house = lambda s: ((s - li) % 12) + 1
    out = {
        "lagna": {"sign": SIGNS[li], "sign_index": li, "house": 1,
                  "lord": SIGN_LORD[li],
                  "means": "what you are — body, health, the self"},
    }
    try:
        from antar_engine.jaimini_engine import (compute_arudha_lagna,
                                                 compute_upapada_lagna)
        jp = _jaimini_planets(chart)
        al = compute_arudha_lagna(li, jp)
        ul = compute_upapada_lagna(li, jp)
        out["arudha"] = {
            "sign": al.sign_name, "sign_index": al.sign, "house": house(al.sign),
            "lord": SIGN_LORD[al.sign],
            "means": "what you SEEM — image, reputation, how the world reads you",
            "a11_sign": SIGNS[(al.sign + 10) % 12],
            "a11_house": house((al.sign + 10) % 12),
        }
        out["upapada"] = {
            "sign": ul.sign_name, "sign_index": ul.sign, "house": house(ul.sign),
            "lord": SIGN_LORD[ul.sign],
            "means": "the marriage — the spouse and the bond",
        }
    except Exception:
        pass
    try:
        from antar_engine.sri_lagna import sri_lagna
        sl = sri_lagna(chart)
        if sl.get("available"):
            out["sri"] = {
                "sign": sl["sign"], "sign_index": sl["sign_index"],
                "house": sl["house_from_lagna"], "lord": sl["lord"],
                "means": "where prosperity settles",
            }
    except Exception:
        pass
    return out


def read_from(chart: dict, reference: str) -> Dict:
    """What sits on the houses that matter, counted FROM the given reference."""
    refs = all_references(chart)
    ref = refs.get(reference)
    if not ref:
        return {"available": False}
    base = ref["sign_index"]
    findings: List[str] = []

    if reference == "arudha":
        # A11 is the classical Jaimini wealth seat — what the world can see you
        # have, as opposed to the 11th from the lagna, which is what you receive.
        a11 = (base + 10) % 12
        occ = _occupants_of_sign(chart, a11)
        if occ:
            good = [p for p in occ if p in BENEFIC]
            bad = [p for p in occ if p in MALEFIC]
            if good:
                findings.append(f"{', '.join(good)} in A11 ({SIGNS[a11]}) — the seat "
                                f"of visible wealth is supported; what he builds is "
                                f"seen to be his.")
            if bad:
                findings.append(f"{', '.join(bad)} in A11 ({SIGNS[a11]}) — visible "
                                f"gains carry friction; standing and money do not "
                                f"arrive together easily.")
        else:
            findings.append(f"A11 ({SIGNS[a11]}) is empty — visible wealth follows "
                            f"its lord {SIGN_LORD[a11]} rather than any occupant.")
        twelfth = (base + 11) % 12
        loss = _occupants_of_sign(chart, twelfth)
        if loss:
            findings.append(f"{', '.join(loss)} in the 12th from the arudha — image "
                            f"costs something to maintain here.")

    elif reference == "upapada":
        # The 2nd from Upapada is the classical seat of the marriage's
        # sustenance. Malefics there are the standard indication of strain.
        second = (base + 1) % 12
        occ = _occupants_of_sign(chart, second)
        bad = [p for p in occ if p in MALEFIC]
        good = [p for p in occ if p in BENEFIC]
        if bad:
            findings.append(f"{', '.join(bad)} in the 2nd from the Upapada "
                            f"({SIGNS[second]}) — the classical indication of strain "
                            f"in sustaining a marriage. It describes difficulty, not "
                            f"an outcome.")
        if good:
            findings.append(f"{', '.join(good)} in the 2nd from the Upapada "
                            f"({SIGNS[second]}) — support for the bond holding.")
        if not occ:
            findings.append(f"The 2nd from the Upapada ({SIGNS[second]}) is empty — "
                            f"the bond follows its lord {SIGN_LORD[second]}.")

    elif reference == "sri":
        for h, label in ((1, "2nd"), (10, "11th")):
            s = (base + h) % 12
            occ = _occupants_of_sign(chart, s)
            if occ:
                findings.append(f"{', '.join(occ)} in the {label} from Sri Lagna "
                                f"({SIGNS[s]}) — where prosperity is held or spent.")

    return {"available": True, "reference": reference,
            "sign": ref["sign"], "house_from_lagna": ref["house"],
            "lord": ref["lord"], "means": ref["means"], "findings": findings}


def references_for(concern: str) -> List[str]:
    return CONCERN_REFERENCE.get((concern or "general").strip().lower(),
                                 ["lagna", "arudha"])


def special_lagna_context(chart: dict, concern: str = "general") -> str:
    """Prompt block naming the reference this question should be read from."""
    refs = references_for(concern)
    lines = ["═══ WHICH REFERENCE THIS QUESTION IS READ FROM ═══"]
    for r in refs:
        rd = read_from(chart, r)
        if not rd.get("available"):
            continue
        lines.append(f"{r.upper()} — {rd['means']}")
        lines.append(f"  falls in {rd['sign']}, house {rd['house_from_lagna']} "
                     f"from the birth ascendant; its lord is {rd['lord']}")
        for f in rd["findings"]:
            lines.append(f"  - {f}")
    if len(lines) == 1:
        return ""
    lines.append("  RULE: a question about IMAGE or standing is read from the arudha, "
                 "not the ascendant — the ascendant is what the person is, the arudha "
                 "is what the world sees. Do not mix the two into one claim.")
    return "\n".join(lines)
