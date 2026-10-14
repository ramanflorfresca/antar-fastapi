"""
Pt. Roop Chand's Lal Kitab remedies, each tied to the chart condition it treats and offered only where that
condition holds (same clause grammar as rc_rules). Plain English and Spanish steps; no planet names.
His principles (from the text): easy and affordable measures; a run is 43 unbroken days unless the text says
otherwise; daylight for day remedies; one measure at a time; start again if a day is missed.
Gems are not part of his method; the only stones here are the two the text itself prescribes.
"""
import json
import os
from typing import List, Optional

from antar_engine import rc_rules as rc

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lk_roop_chand_remedies.json")
_cache: Optional[List[dict]] = None


def load_remedies(path: str = DATA_PATH) -> List[dict]:
    global _cache
    if path == DATA_PATH and _cache is not None:
        return _cache
    try:
        out = json.load(open(path)).get("remedies", [])
    except Exception:
        out = []
    if path == DATA_PATH:
        _cache = out
    return out


def applying(state: dict, remedies: Optional[List[dict]] = None) -> List[dict]:
    remedies = load_remedies() if remedies is None else remedies
    return [r for r in remedies if all(rc.holds(c, state) for c in r.get("requires", []))]


def subjects_of(remedy: dict) -> List[str]:
    return rc.subjects_of({"topics": remedy.get("topics", [])})


def render(remedy: dict, lang: str = "en") -> Optional[dict]:
    """Remedy in one language, or None if that language is not available."""
    if lang == "es":
        if not remedy.get("steps_es"):
            return None
        steps, problem, dur = remedy["steps_es"], remedy.get("problem_es") or remedy["problem"], remedy.get("duration_es")
    else:
        steps, problem, dur = remedy["steps"], remedy["problem"], remedy.get("duration")
    return {"rule_id": f"LKR.{remedy['id']}", "problem": problem, "steps": steps, "do": " ".join(steps),
            "timing": "", "duration": dur or ""}
