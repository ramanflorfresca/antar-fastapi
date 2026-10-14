"""Plain-English description of a rule's conditions, for the owner to read and edit rules (not shown to users)."""
import json
from typing import List

ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def _h(n):
    return ORD.get(n, f"{n}th")


def _hs(v):
    return " / ".join(_h(x) for x in v)


def clause(c: dict) -> str:
    fr = {"kp": "[KP chart] ", "varsha": "[solar-return chart] "}.get(c.get("frame"), "")
    p = c.get("planet")
    if "unparsed" in c:
        return f"(not machine-readable: {c['unparsed']}) - never applies"
    if "lagna_sign" in c:
        return f"{c['lagna_sign']} rises"
    if "chart" in c and len(c) <= 2 and "planet" not in c:
        return f"chart is {c['chart']}"
    if "dasha_signifies" in c:
        d = c["dasha_signifies"]
        return f"{fr}the {d['level'].upper()} lord signifies {d.get('mode','any')} of houses {_hs(d['houses'])}"
    if "dasha" in c:
        d = c["dasha"]
        return f"the {d['level'].upper()} (period) lord is {' or '.join(d.get('lords', []))}"
    if "transit" in c:
        t = c["transit"]
        return f"{t['planet']} transits the {_hs(t['houses'])} house from {t.get('from','lagna')}"
    if "transit_conj" in c:
        t = c["transit_conj"]
        return f"{t['planet']} transits the sign of natal {t['with']}"
    if "transit_deg" in c:
        t = c["transit_deg"]
        return f"{t['planet']} transits {t['sign']} {t['from_deg']}-{t['to_deg']} degrees"
    if "transit_nakshatra" in c:
        t = c["transit_nakshatra"]
        return f"{t['planet']} transits {t['nakshatra']} nakshatra"
    if "transit_sign" in c:
        t = c["transit_sign"]
        return f"{t['planet']} transits {' or '.join(t['signs'])}"
    if "transit_aspect" in c:
        t = c["transit_aspect"]
        return f"transiting {t['a']} and {t['b']} are {t['aspect']} (orb {t.get('orb',8)})"
    if "age_year" in c:
        return f"running year of life is {c['age_year']}"
    if "cusp" in c:
        parts = [f"{fr}cusp {c['cusp']}"]
        for k in ("sub_lord_signifies", "sub_lord_star_lord_signifies"):
            if k in c:
                parts.append(f"{k.replace('_',' ')} {c.get('mode','any')} of houses {_hs(c[k])}")
        for k in ("sub_lord", "star_lord", "sign_lord"):
            if k in c:
                parts.append(f"{k.replace('_',' ')} = {c[k]}")
        if "sub_lord_in_house" in c:
            parts.append(f"sub lord in house {_hs(c['sub_lord_in_house'])}")
        return ", ".join(parts)
    if p and "signifies" in c:
        return f"{fr}{p} signifies {c.get('mode','any')} of houses {_hs(c['signifies'])}"
    if p and "star_lord_signifies" in c:
        return f"{fr}{p}'s star lord signifies {c.get('mode','any')} of houses {_hs(c['star_lord_signifies'])}"
    if p and "in_house" in c:
        return f"{fr}{p} sits in the {_hs(c['in_house'])} cusp house"
    if p and any(k in c for k in ("star_lord", "sub_lord", "sign_lord")) and "in_houses" not in c:
        k = next(k for k in ("star_lord", "sub_lord", "sign_lord") if k in c)
        return f"{fr}{p}'s {k.replace('_',' ')} is {c[k]}"
    if p and "in_houses_from" in c:
        return f"{p} is in the {_hs(c['houses'])} house counted from {c['in_houses_from']}"
    if p and "in_houses" in c:
        return f"{p} is in the {_hs(c['in_houses'])} house"
    if p and "not_in_houses" in c:
        return f"{p} is not in the {_hs(c['not_in_houses'])} house"
    if p and "dignity" in c:
        return f"{p} is {' or '.join(c['dignity'])}"
    if p and "touches" in c:
        return f"{p} is in, or aspects the sign of, {c['touches']}"
    if p and "in" in c and "with" not in c:
        return f"{p} is in house(s) {c['in']}"
    if p and "not_in" in c:
        return f"{p} is not in house(s) {c['not_in']}"
    if p and "with" in c:
        return f"{p} is with {c['with']}"
    if "a" in c and "b" in c and "relation" in c:
        return f"{c['a']} and {c['b']}: {c['relation'].replace('_',' ')}"
    if "house" in c and "empty" in c:
        return f"house {c['house']} is {'empty' if c['empty'] else 'occupied'}"
    if "house" in c and "holds_any" in c:
        return f"house {c['house']} holds any of {', '.join(c['holds_any'])}"
    if "house" in c and "holds_any_benefic" in c:
        return f"house {c['house']} holds a benefic"
    if "house" in c and "holds_any_malefic" in c:
        return f"house {c['house']} {'holds' if c['holds_any_malefic'] else 'holds no'} malefic"
    if "from" in c and "houses" in c:
        w = "holds any of" if "holds_any" in c else "holds none of"
        return f"houses {_hs(c['houses'])} from {c['from']} {w} {', '.join(c.get('holds_any') or c.get('holds_none_of') or [])}"
    if "houses" in c and "holds_any" in c:
        return f"houses {c['houses']} hold any of {', '.join(c['holds_any'])}"
    if c.get("kendras_all_occupied"):
        return "all four kendras (1,4,7,10) are occupied"
    if "planets_in_houses" in c:
        return f"at least {c.get('at_least','all')} of {', '.join(c['planets_in_houses'])} are in houses {c['houses']}"
    if "point" in c:
        return f"{c['point']} falls in the {_hs(c['in'])} house from {c['house_from']}"
    return json.dumps(c)


_ENT = {"AK": "Atmakaraka", "AmK": "Amatyakaraka", "BK": "Bhratrukaraka", "MK": "Matrukaraka", "PK": "Putrakaraka",
        "GK": "Gnatikaraka", "DK": "Darakaraka", "AL": "Arudha Lagna", "UL": "Upapada", "A7": "Darapada", "KL": "Karakamsha"}


def _words(text: str) -> str:
    import re
    text = re.sub(r"\bL(\d{1,2})\b", lambda m: "lord of house " + m.group(1), text)
    return re.sub(r"\b(AK|AmK|BK|MK|PK|GK|DK|AL|UL|A7|KL)\b", lambda m: _ENT[m.group(1)], text)


def describe(clauses: List[dict]) -> str:
    return _words(" AND ".join(clause(c) for c in (clauses or []))) or "(always, for any chart)"
