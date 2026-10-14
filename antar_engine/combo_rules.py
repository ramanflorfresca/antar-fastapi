"""
B.V. Raman, "Three Hundred Important Combinations" (Part I, entries 1-162; the file we hold stops there), applied only
where their conditions hold in the chart. Each combination was written as machine-checkable clauses (see `holds`),
read from the lagna with whole signs and the standard Parashari lords. Rules whose condition needs strength,
navamsa, degrees, sign types or counts of signs were dropped when the data was built, not guessed.

State: {"lagna": 0-11, "signs": {planet: 0-11}, "gender": "male"|"female"|None,
        optional Jaimini data: "karakas": {"AK": planet, "AmK": ..., "BK", "MK", "PK", "GK", "DK"},
                               "points": {"AL": sign, "UL": sign, "A7": sign, "KL": sign}}

Entities: planet names, "L<k>" (lord of house k), the seven karakas "AK".."DK", and sign points "AL" (arudha lagna),
"UL" (upapada), "A7" (darapada), "KL" (karakamsha), "lagna". Extra clauses for Jaimini rules:
  {"point": "AL", "house_from": "lagna", "in": [10, 11]}     house of a sign point (or planet's sign) counted from another
  {"planet": "AmK", "touches": "AL"}                          planet is in that sign or aspects it (rasi drishti)
"""
import json
import os
import re
from typing import Dict, List, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raman_combinations_rules.json")
PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
LORD = {0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars", 8: "Jupiter",
        9: "Saturn", 10: "Saturn", 11: "Jupiter"}
OWN = {"Sun": {4}, "Moon": {3}, "Mars": {0, 7}, "Mercury": {2, 5}, "Jupiter": {8, 11}, "Venus": {1, 6}, "Saturn": {9, 10}}
EXALT = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBIL = {"Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0}
ASPECT_HOUSES = {"Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10)}      # graha drishti, counted from own sign
BENEFIC = ("Jupiter", "Venus", "Mercury")
MALEFIC = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")
_cache: Optional[List[dict]] = None


def load_rules(path: str = DATA_PATH) -> List[dict]:
    global _cache
    if path == DATA_PATH and _cache is not None:
        return _cache
    try:
        rules = json.load(open(path)).get("rules", [])
    except Exception:
        rules = []
    if path == DATA_PATH:
        _cache = rules
    return rules


KARAKAS = ("AK", "AmK", "BK", "MK", "PK", "GK", "DK")


def _planet(state: dict, ent) -> Optional[str]:
    """ENTITY -> planet name ('Moon', 'L5' = lord of the 5th, 'L1' = lagna lord, 'AK' = the atmakaraka)."""
    if isinstance(ent, str) and ent in PLANETS:
        return ent
    if isinstance(ent, str) and ent in KARAKAS:
        return (state.get("karakas") or {}).get(ent)
    m = re.fullmatch(r"L(\d{1,2})", str(ent))
    if m and 1 <= int(m.group(1)) <= 12:
        return LORD[(state["lagna"] + int(m.group(1)) - 1) % 12]
    return None


def _sign(state: dict, ent) -> Optional[int]:
    if ent == "lagna":
        return state["lagna"]
    if isinstance(ent, str) and ent in (state.get("points") or {}):
        return state["points"][ent]
    p = _planet(state, ent)
    return state["signs"].get(p) if p else None


def _house(state: dict, planet_ent, frm="lagna") -> Optional[int]:
    s, o = _sign(state, planet_ent), _sign(state, frm)
    return None if s is None or o is None else (s - o) % 12 + 1


def _aspects(state: dict, a: str, b: str) -> bool:
    """Graha drishti of planet a on the sign of planet b (nodes cast none)."""
    if a not in ASPECT_HOUSES and a not in ("Sun", "Moon", "Mercury", "Venus"):
        return False
    sa, sb = state["signs"].get(a), state["signs"].get(b)
    if sa is None or sb is None:
        return False
    return ((sb - sa) % 12 + 1) in ASPECT_HOUSES.get(a, (7,))


def _signs_in_house(state: dict, h: int) -> int:
    return (state["lagna"] + h - 1) % 12


def holds(c: dict, state: dict) -> bool:
    if "unparsed" in c or c.get("frame") in ("kp", "varsha"):
        return False            # KP and solar-return clauses have their own evaluators
    if "chart" in c and len(c) == 1:
        return state.get("gender") == c["chart"]
    signs = state["signs"]
    if "kendras_all_occupied" in c:
        return all(any((s - state["lagna"]) % 12 + 1 == k for s in signs.values()) for k in (1, 4, 7, 10))
    if "planets_in_houses" in c:
        n = sum(1 for p in c["planets_in_houses"] if p in signs and _house(state, p) in c["houses"])
        return n >= c.get("at_least", len(c["planets_in_houses"]))
    if "house" in c:
        sg = _signs_in_house(state, c["house"])
        here = [p for p, s in signs.items() if s == sg]
        if "empty" in c:
            return (not here) if c["empty"] else bool(here)
        if "holds_any" in c:
            return any(p in here for p in c["holds_any"])
        if c.get("holds_any_benefic"):
            return any(p in here for p in BENEFIC)
        if c.get("holds_any_malefic"):
            return any(p in here for p in MALEFIC)
        return False
    if "from" in c and "houses" in c and ("holds_any" in c or "holds_none_of" in c) and "planet" not in c:
        base = _sign(state, c["from"])
        if base is None:
            return False
        targets = {(base + h - 1) % 12 for h in c["houses"]}
        listed = c.get("holds_any") or c.get("holds_none_of")
        there = any(signs.get(p) in targets for p in listed)
        return there if "holds_any" in c else not there
    if "point" in c and "house_from" in c and "in" in c:
        a, b = _sign(state, c["point"]), _sign(state, c["house_from"])
        return a is not None and b is not None and ((a - b) % 12 + 1) in c["in"]
    if "planet" in c and "touches" in c:
        p = _planet(state, c["planet"])
        tgt = _sign(state, c["touches"])
        if not p or p not in signs or tgt is None:
            return False
        from antar_engine.jaimini_engine import get_rashi_drishti
        return signs[p] == tgt or tgt in get_rashi_drishti(signs[p])
    if "a" in c and "b" in c and "relation" in c:
        a, b = _planet(state, c["a"]), _planet(state, c["b"])
        if not a or not b or a not in signs or b not in signs:
            return False
        rel = c["relation"]
        if rel == "conjunct":
            return a != b and signs[a] == signs[b]
        if rel == "a_aspects_b":
            return _aspects(state, a, b)
        if rel == "mutual_aspect":
            return _aspects(state, a, b) and _aspects(state, b, a)
        if rel == "exchange":
            return a != b and signs[a] in OWN.get(b, ()) and signs[b] in OWN.get(a, ())
        h = (signs[b] - signs[a]) % 12 + 1
        if rel == "kendra_from_each_other":
            return h in (1, 4, 7, 10)
        if rel == "trine_from_each_other":
            return h in (1, 5, 9)
        return False
    if "planet" in c:
        p = _planet(state, c["planet"])
        if not p or p not in signs:
            return False
        if "dignity" in c:
            s = signs[p]
            ok = set(c["dignity"])
            return (("own" in ok and s in OWN.get(p, ())) or ("exalted" in ok and EXALT.get(p) == s)
                    or ("debilitated" in ok and DEBIL.get(p) == s))
        if "in_houses_from" in c:
            h = _house(state, p, c["in_houses_from"])
            return h in c.get("houses", [])
        if "in_houses" in c:
            return _house(state, p) in c["in_houses"]
        if "not_in_houses" in c:
            return _house(state, p) not in c["not_in_houses"]
    return False


def applies(rule: dict, state: dict) -> bool:
    return all(holds(c, state) for c in rule.get("requires", []))


def applying(state: dict, rules: Optional[List[dict]] = None) -> List[dict]:
    rules = load_rules() if rules is None else rules
    return [r for r in rules if applies(r, state)]


SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
              "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
              "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
              "Uttara Bhadrapada", "Revati"]
ASPECT_ANGLES = {"conjunct": 0.0, "sextile": 60.0, "square": 90.0, "trine": 120.0, "opposition": 180.0}
IMPERSONAL_KEYS = ('"transit_deg"', '"transit_nakshatra"', '"transit_sign"', '"transit_aspect"')


def is_impersonal(rule: dict) -> bool:
    """True when nothing in the rule reads this person's chart or periods: same answer for everyone on a given date."""
    if rule.get("requires"):
        return False
    acts = rule.get("activation") or []
    return bool(acts) and all(any(k in json.dumps(a) for k in IMPERSONAL_KEYS) for a in acts)


def act_holds(a: dict, state: dict) -> bool:
    """Activation clause at a date. state also carries 'periods' {md, ad, pd, sd}, 'transit' {planet: sign}, 'age_year'."""
    if "unparsed" in a or a.get("frame") in ("kp", "varsha"):
        return False
    if "dasha" in a:
        d = a["dasha"]
        lord = (state.get("periods") or {}).get(d.get("level"))
        if not lord:
            return False
        wanted = {_planet(state, e) for e in d.get("lords", [])}
        return lord in wanted
    if "transit" in a:
        t = a["transit"]
        ts = (state.get("transit") or {}).get(t.get("planet"))
        ref = _sign(state, t.get("from", "lagna"))
        if ts is None or ref is None:
            return False
        return ((ts - ref) % 12 + 1) in t.get("houses", [])
    if "transit_conj" in a:
        t = a["transit_conj"]
        ts = (state.get("transit") or {}).get(t.get("planet"))
        tgt = _sign(state, t.get("with"))
        return ts is not None and tgt is not None and ts == tgt
    if "age_year" in a:
        return state.get("age_year") in a["age_year"]
    lons = (state.get("transit_lon_trop") if a.get("zodiac") == "tropical" else state.get("transit_lon")) or {}
    if "transit_deg" in a:
        t = a["transit_deg"]
        lon = lons.get(t.get("planet"))
        sign = SIGNS.index(t["sign"]) if t.get("sign") in SIGNS else None
        return lon is not None and sign is not None and int(lon // 30) == sign and t["from_deg"] <= lon % 30 < t["to_deg"] + (1e-9 if t["to_deg"] >= 30 else 0)
    if "transit_nakshatra" in a:
        t = a["transit_nakshatra"]
        lon = lons.get(t.get("planet"))
        if lon is None:
            return False
        if a.get("zodiac") == "tropical":                  # Butaney's table starts Ashwini at 23deg20' Pisces
            lon = (lon - 353.0 - 1.0 / 3.0) % 360.0
        return NAKSHATRAS[int(lon // (360 / 27)) % 27] == t.get("nakshatra")
    if "transit_sign" in a:
        t = a["transit_sign"]
        lon = lons.get(t.get("planet"))
        return lon is not None and SIGNS[int(lon // 30) % 12] in t.get("signs", [])
    if "transit_aspect" in a:
        t = a["transit_aspect"]
        la, lb = lons.get(t.get("a")), lons.get(t.get("b"))
        want = ASPECT_ANGLES.get(t.get("aspect"))
        if la is None or lb is None or want is None:
            return False
        sep = abs(la - lb) % 360.0
        sep = min(sep, 360.0 - sep)
        return abs(sep - want) <= float(t.get("orb", 8))
    return False


def timed_ok(rule: dict, state: dict) -> bool:
    """Natal requires AND every activation clause hold (state carries the date's periods and transits)."""
    return applies(rule, state) and all(act_holds(a, state) for a in rule.get("activation", []))
