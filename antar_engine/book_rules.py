"""
Rules read from the astrology library (K.N. Rao, B.V. Raman and others), decomposed by readers into clauses
(see BOOK_RULES_SPEC): natal conditions in `requires`, timing conditions in `activation`. A rule applies only where its
conditions hold; timed rules are evaluated at a date against the Vimshottari periods and the transits.
"""
import json
import os
from typing import List, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "book_rules.json")
_cache: Optional[List[dict]] = None
BOOK_LABEL = {"kn_rao": "K.N. Rao", "bv_raman": "B.V. Raman", "jaimini_sutras": "Jaimini Sutras",
              "jataka_parijata": "Jataka Parijata",
              "chatterjee_medical": "Medical astrology (Chatterjee)", "butaney_prices": "Butaney, market timing"}


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


def label(rule: dict) -> str:
    b = rule.get("book", "")
    for k, v in BOOK_LABEL.items():
        if b.startswith(k):
            return v
    return "Classical text"
