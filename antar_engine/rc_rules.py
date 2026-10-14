"""
Roop Chand Lal Kitab rules, applied only where their conditions hold.

Source authority: Pt. Roop Chand Joshi's "Text Book of Lal Kitab" (the five classics) only. The rules in
data/lk_roop_chand_rules.json were decomposed from the text into atomic rules with machine-checkable
conditions (see the grammar in `holds`; clause {"lagna_sign": "Cancer"} reads the rising sign). A rule whose condition cannot be expressed is flagged `unparsed`
and NEVER applies. Rules about death, longevity, disease, harm to relatives and occult acts are excluded
when the data is built. House numbering is the fixed frame (Aries = house 1), per the owner.

kind "natal"  : planet sits in `houses` in the birth chart and every `requires` clause holds.
kind "annual" : planet reaches `annual_houses` in the year chart (varshphal) and every clause holds
                (clauses with "chart": "annual" read the year chart, the rest read the birth chart).
"""
import json
import os
from typing import Dict, Iterable, List, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lk_roop_chand_rules.json")
PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
TOPIC_SUBJECTS = {"money": ["money"], "career": ["career", "job", "business"], "marriage": ["marriage", "love"],
                  "children": ["children"], "fame": ["career"], "property": ["property"], "foreign": ["foreign"],
                  "education": ["education"], "health": ["health"], "spiritual": ["spirituality"], "family": [], "other": []}

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


def _chart_houses(state: dict, which: str) -> Dict[str, int]:
    return state.get("annual" if which == "annual" else "natal") or {}


def holds(clause: dict, state: dict) -> bool:
    """state = {"natal": {planet: house}, "annual": {planet: house}|None, "gender": "male"|"female"|None}.
    Unknown or unparsed clauses do not hold."""
    if "unparsed" in clause:
        return False
    if "lagna_sign" in clause:
        return state.get("lagna_sign") == clause["lagna_sign"]
    if "chart" in clause and clause["chart"] in ("male", "female") and len(clause) == 1:
        return state.get("gender") == clause["chart"]
    which = clause.get("chart", "natal")
    houses = _chart_houses(state, which)
    if which == "annual" and not houses:
        return False
    if "planet" in clause:
        p = clause["planet"]
        if p not in houses:
            return False
        if "in" in clause:
            return houses[p] in clause["in"]
        if "not_in" in clause:
            return houses[p] not in clause["not_in"]
        if "with" in clause:
            q = clause["with"]
            return q in houses and houses[q] == houses[p]
        return False
    if "house" in clause and "empty" in clause:
        occupied = any(h == clause["house"] for h in houses.values())
        return (not occupied) if clause["empty"] else occupied
    if "houses" in clause and "holds_any" in clause:
        return any(houses.get(p) in clause["houses"] for p in clause["holds_any"])
    if "houses" in clause and "holds_none_of" in clause:
        return not any(houses.get(p) in clause["houses"] for p in clause["holds_none_of"])
    return False


def rule_applies(rule: dict, state: dict) -> bool:
    if rule.get("sensitive"):
        return False
    natal, annual = state.get("natal") or {}, state.get("annual")
    p = rule.get("planet")
    if rule.get("kind") == "annual":
        if not annual or not p or p not in annual or not rule.get("annual_houses"):
            return False
        if annual[p] not in rule["annual_houses"]:
            return False
    else:
        if rule.get("houses") is not None:
            if not p or p not in natal or natal[p] not in rule["houses"]:
                return False
    return all(holds(c, state) for c in rule.get("requires", []))


def applying(state: dict, kind: Optional[str] = None, rules: Optional[List[dict]] = None) -> List[dict]:
    rules = load_rules() if rules is None else rules
    return [r for r in rules if (kind is None or r.get("kind") == kind) and rule_applies(r, state)]


def subjects_of(rule: dict) -> List[str]:
    out = []
    for t in rule.get("topics", []):
        for s in TOPIC_SUBJECTS.get(t, []):
            if s not in out:
                out.append(s)
    return out


def merge_files(paths: Iterable[str]) -> List[dict]:
    """Combine the reader outputs: drop sensitive rules, drop rules with no effect text, drop exact duplicates."""
    seen, out = set(), []
    for p in paths:
        for r in json.load(open(p)).get("rules", []):
            if r.get("sensitive") or not (r.get("effect") or "").strip() or r.get("effect") == "(omitted)":
                continue
            key = (r.get("kind"), r.get("planet"), tuple(r.get("houses") or ()), tuple(r.get("annual_houses") or ()),
                   json.dumps(r.get("requires", []), sort_keys=True), r.get("tone"), r.get("effect"))
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
    return out
