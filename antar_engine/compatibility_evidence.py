"""
Relational evidence — name the placement, don't just grade it.

compatibility_capability.py made the hiring layer specific by citing the actual
D-10 placement behind the score. This module does the same job for the six
*relational* layers, so a love or marriage reading can say

    "Yoni is Tiger to Mongoose — 1 of 4."

instead of only

    "There's real chemistry, though it needs tending."

Design rules
------------
* Every clause is built from a value the engine actually computed. If the fact
  isn't there, we return "" and the caller says nothing — silence beats a
  reassuring generality.
* Clauses are short. They append to the existing template line, which keeps the
  established voice and stays translatable; the evidence is the new part.
* Nothing here re-scores anything. It only explains the score that exists.
"""

from __future__ import annotations

from antar_engine.compatibility_synastry import _planets_in_house

_COMPAT_WORD = {"strong": "well matched", "moderate": "workable",
                "challenging": "at odds"}

# Nakshatra-kuta components carry a_value/b_value already — these are the ones
# worth quoting to a reader, with a plain-language gloss of what they govern.
_KUTA_GLOSS = {
    "Yoni":         "physical rhythm",
    "Gana":         "temperament",
    "Bhakoot":      "the emotional axis",
    "Nadi":         "constitutional health",
    "Varna":        "how you each meet duty",
    "Tara":         "mutual fortune",
    "Vashya":       "natural pull",
    "Graha Maitri": "mental rapport",
}


def _comp(engine_result: dict, name: str) -> dict | None:
    for c in (engine_result.get("ashtakoot") or {}).get("components", []) or []:
        if c.get("name") == name:
            return c
    return None


def _kuta_clause(engine_result: dict, name: str) -> str:
    """'Yoni is Tiger to Mongoose — 1 of 4.'"""
    c = _comp(engine_result, name)
    if not c:
        return ""
    a, b = c.get("a_value"), c.get("b_value")
    if not a or not b:
        return ""
    # Kuta values sometimes carry a parenthetical gloss; keep the head word.
    a = str(a).split("(")[0].strip()
    b = str(b).split("(")[0].strip()
    if a == b:
        return f"{name} matches on both sides ({a}) — {c.get('score')} of {c.get('max')}."
    return f"{name} is {a} to {b} — {c.get('score')} of {c.get('max')}."


def _house_clause(chart_a: dict, chart_b: dict, house: int, b_name: str) -> str:
    """'Priya's Venus and Jupiter fall in your 7th.'"""
    occ = _planets_in_house(chart_a, chart_b, house)
    if not occ:
        return ""
    names = [p for p, _ in occ][:3]
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    ordinal = {7: "7th", 10: "10th", 11: "11th", 1: "1st"}.get(house, f"{house}th")
    verb = "falls" if len(names) == 1 else "fall"
    return f"{b_name}'s {joined} {verb} in your {ordinal}."


def _navamsa_clause(engine_result: dict, planet: str) -> str:
    """'Venus sits well matched across the navamsas.'"""
    d9 = engine_result.get("d9_navamsa") or {}
    val = d9.get(f"{planet.lower()}_compatibility")
    if not val:
        return ""
    return f"{planet} reads {_COMPAT_WORD.get(val, val)} across the navamsas."


def _dasha_clause(engine_result: dict, a_name: str, b_name: str) -> str:
    dt = engine_result.get("dasha_timing") or {}
    if dt.get("alignment") == "unknown":
        return ""
    ta, tb = dt.get("type_a"), dt.get("type_b")
    pa = str(dt.get("person_a_dasha") or "").split("-")[0]
    pb = str(dt.get("person_b_dasha") or "").split("-")[0]
    if not (ta and tb and pa and pb):
        return ""
    if ta == tb:
        return f"You are both in {ta} periods ({pa} and {pb})."
    return f"You are in a {ta} period ({pa}), {b_name} in {tb} ({pb})."


def _mercury_clause(engine_result: dict, chart_a: dict, chart_b: dict,
                    b_name: str) -> str:
    try:
        from antar_engine.compatibility_synastry import mercury_cross_compat
        m = mercury_cross_compat(chart_a, chart_b)
    except Exception:
        return ""
    a_s, b_s = m.get("a_sign"), m.get("b_sign")
    if not a_s or not b_s:
        return ""
    if a_s == b_s:
        return f"Both Mercuries sit in {a_s} — you process the same way."
    return f"Your Mercury is in {a_s}, {b_name}'s in {b_s}."


def _aspect_clause(engine_result: dict, chart_a: dict, chart_b: dict) -> str:
    try:
        from antar_engine.compatibility_synastry import cross_aspect_harmony
        notable = (cross_aspect_harmony(chart_a, chart_b) or {}).get("notable") or []
    except Exception:
        return ""
    if not notable:
        return ""
    return str(notable[0]).capitalize() + "."


# layer -> ordered list of clause builders; first non-empty wins.
def evidence_for(layer: str, engine_result: dict, chart_a: dict, chart_b: dict,
                 a_name: str, b_name: str) -> str:
    """One short evidence clause for a relational layer, or ''."""
    try:
        if layer == "soul":
            return (_kuta_clause(engine_result, "Graha Maitri")
                    or _kuta_clause(engine_result, "Varna"))
        if layer == "chemistry":
            return (_kuta_clause(engine_result, "Yoni")
                    or _navamsa_clause(engine_result, "Venus")
                    or _navamsa_clause(engine_result, "Mars"))
        if layer == "public":
            return (_house_clause(chart_a, chart_b, 10, b_name)
                    or _house_clause(chart_a, chart_b, 7, b_name)
                    or _house_clause(chart_a, chart_b, 11, b_name))
        if layer == "lifepath":
            return (_dasha_clause(engine_result, a_name, b_name)
                    or _kuta_clause(engine_result, "Bhakoot"))
        if layer == "communication":
            return (_mercury_clause(engine_result, chart_a, chart_b, b_name)
                    or _kuta_clause(engine_result, "Gana"))
        if layer == "friction":
            return (_kuta_clause(engine_result, "Nadi")
                    or _aspect_clause(engine_result, chart_a, chart_b))
    except Exception:
        return ""
    return ""
