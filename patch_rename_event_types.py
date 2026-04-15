"""
patch_rename_event_types.py
============================
Rename event keys in dasha_event_mapper.py from culturally-specific Vedic
labels to culture-neutral activation labels.

Uses landmark string search only — never line numbers.
Idempotent: safe to run twice.
"""

import shutil
import os

TARGET = "antar_engine/dasha_event_mapper.py"
BAK    = TARGET + ".bak_rename_events"

# ── backup ─────────────────────────────────────────────────────────────────
shutil.copy2(TARGET, BAK)
print(f"[backup] {BAK}")

with open(TARGET, "r") as f:
    src = f.read()

original_src = src  # keep for diff reporting

# ===========================================================================
# (D) + (E)  Insert EVENT_ALIASES, normalize_event_key, EVENT_DISPLAY_LABELS,
#             EVENT_DESCRIPTION  — right after HOUSE_LORDS closing brace
# ===========================================================================

ALIASES_BLOCK = '''
# ---------------------------------------------------------------------------
# Backward-compatibility alias map (old key → new key)
# External callers (main.py, predictions.py) can still pass old keys.
# ---------------------------------------------------------------------------
EVENT_ALIASES = {
    "marriage":         "serious_partnership_began",
    "divorce":          "serious_partnership_ended",
    "first_child":      "family_expansion_first",
    "second_child":     "family_expansion_second",
    "foreign_move":     "major_relocation",
    "property":         "major_acquisition",
    "career_change":    "career_pivot",
    "mother_death":     "loss_of_mother",
    "father_death":     "loss_of_father",
    "business_failure": "professional_setback",
    "legal_trouble":    "legal_entanglement",
    "financial_loss":   "financial_disruption",
}


def normalize_event_key(key: str) -> str:
    """Accept old or new event key, always return new canonical key."""
    return EVENT_ALIASES.get(key, key)


# ---------------------------------------------------------------------------
# Human-readable display labels (for frontend / Ask Antar)
# ---------------------------------------------------------------------------
EVENT_DISPLAY_LABELS = {
    "serious_partnership_began":  "Serious partnership window",
    "serious_partnership_ended":  "Partnership transition window",
    "family_expansion_first":     "Family expansion (first)",
    "family_expansion_second":    "Family expansion (second)",
    "major_relocation":           "Major relocation window",
    "major_acquisition":          "Major acquisition window",
    "career_pivot":               "Career pivot window",
    "loss_of_mother":             "Loss of mother",
    "loss_of_father":             "Loss of father",
    "professional_setback":       "Professional setback window",
    "legal_entanglement":         "Legal entanglement window",
    "financial_disruption":       "Financial disruption window",
}

EVENT_DESCRIPTION = {
    "serious_partnership_began": (
        "A serious relationship beginning, deepening, or major commitment moment "
        "— marriage, engagement, moving in together, or a partnership that defines "
        "this period of life."
    ),
    "serious_partnership_ended": (
        "End or major transition of a significant partnership — separation, divorce, "
        "or a relationship that fundamentally changed shape."
    ),
    "family_expansion_first": (
        "Arrival of a first significant family addition — biological child, adoption, "
        "step-child, or someone you took primary responsibility for."
    ),
    "family_expansion_second": (
        "Arrival of a second significant family addition."
    ),
    "major_relocation": (
        "Significant geographical relocation — moving abroad, moving to a new region, "
        "or extended life elsewhere."
    ),
    "major_acquisition": (
        "Major acquisition of property, business, or significant asset."
    ),
    "career_pivot": (
        "Major career direction change, leadership transition, or new professional chapter."
    ),
    "loss_of_mother": "Loss of mother or maternal figure.",
    "loss_of_father": "Loss of father or paternal figure.",
    "professional_setback": (
        "Significant professional difficulty — business failure, major loss, "
        "sustained income disruption."
    ),
    "legal_entanglement": (
        "Significant legal involvement — lawsuit, dispute, regulatory issue."
    ),
    "financial_disruption": (
        "Significant financial difficulty — debt, loss, sustained money pressure."
    ),
}

'''

# Insert after the HOUSE_LORDS closing brace — landmark: the line that ends the dict
HOUSE_LORDS_END = '"Pisces":      {5: "Moon",    7: "Mercury", 9: "Mars",    12: "Saturn"},\n}'

if ALIASES_BLOCK.strip() not in src:
    assert HOUSE_LORDS_END in src, "Landmark not found: HOUSE_LORDS closing brace"
    src = src.replace(
        HOUSE_LORDS_END,
        HOUSE_LORDS_END + "\n" + ALIASES_BLOCK,
        1
    )
    print("[patch D+E] Inserted EVENT_ALIASES, normalize_event_key, EVENT_DISPLAY_LABELS, EVENT_DESCRIPTION")
else:
    print("[skip D+E] Already inserted")


# ===========================================================================
# (A)  Rename keys in _get_priorities() dict
# ===========================================================================

OLD_PRIORITIES = '''    p = {
        "marriage":     _build_marriage_priority(lagna),
        "foreign_move": _build_foreign_priority(lagna),
        "first_child":  _build_first_child_priority(lagna),
        "second_child": _build_second_child_priority(lagna),
        "divorce":      _build_divorce_priority(lagna),
        "mother_death": _build_mother_death_priority(lagna),
        "property":     _build_property_priority(lagna),
    }'''

NEW_PRIORITIES = '''    p = {
        "serious_partnership_began":  _build_marriage_priority(lagna),
        "major_relocation":           _build_foreign_priority(lagna),
        "family_expansion_first":     _build_first_child_priority(lagna),
        "family_expansion_second":    _build_second_child_priority(lagna),
        "serious_partnership_ended":  _build_divorce_priority(lagna),
        "loss_of_mother":             _build_mother_death_priority(lagna),
        "major_acquisition":          _build_property_priority(lagna),
    }'''

if OLD_PRIORITIES in src:
    src = src.replace(OLD_PRIORITIES, NEW_PRIORITIES, 1)
    print("[patch A] Renamed keys in _get_priorities()")
elif NEW_PRIORITIES in src:
    print("[skip A] _get_priorities() already patched")
else:
    raise RuntimeError("Landmark not found: _get_priorities() dict")


# ===========================================================================
# (B)  Rename keys in AGE_RANGES dict
# ===========================================================================

OLD_AGE_RANGES = '''AGE_RANGES = {
    "marriage":     (20, 35),
    "foreign_move": (8, 45),   # lowered — childhood relocations common
    "first_child":  (22, 38),
    "second_child": (24, 43),
    "divorce":      (25, 55),
    "mother_death": (15, 75),
    "property":     (30, 65),
}'''

NEW_AGE_RANGES = '''AGE_RANGES = {
    "serious_partnership_began":  (20, 35),
    "major_relocation":           (8, 45),   # lowered — childhood relocations common
    "family_expansion_first":     (22, 38),
    "family_expansion_second":    (24, 43),
    "serious_partnership_ended":  (25, 55),
    "loss_of_mother":             (15, 75),
    "major_acquisition":          (30, 65),
}'''

if OLD_AGE_RANGES in src:
    src = src.replace(OLD_AGE_RANGES, NEW_AGE_RANGES, 1)
    print("[patch B] Renamed keys in AGE_RANGES")
elif NEW_AGE_RANGES in src:
    print("[skip B] AGE_RANGES already patched")
else:
    raise RuntimeError("Landmark not found: AGE_RANGES dict")


# ===========================================================================
# (C-1) Add normalize_event_key call at start of find_event_window
#        so external callers with old keys still work
# ===========================================================================

OLD_FIND_START = '''def find_event_window(
    event_type: str,
    lagna: str,
    birth_year: int,
    ads: list,
    after_year: Optional[int] = None,
    before_year: Optional[int] = None,
) -> Optional[dict]:
    """
    Find the most likely MD+AD window for a life event.
    Works for any lagna and any dasha sequence.
    """
    min_age, max_age = AGE_RANGES.get(event_type, (20, 50))'''

NEW_FIND_START = '''def find_event_window(
    event_type: str,
    lagna: str,
    birth_year: int,
    ads: list,
    after_year: Optional[int] = None,
    before_year: Optional[int] = None,
) -> Optional[dict]:
    """
    Find the most likely MD+AD window for a life event.
    Works for any lagna and any dasha sequence.
    Accepts old or new event keys via normalize_event_key().
    """
    event_type = normalize_event_key(event_type)
    min_age, max_age = AGE_RANGES.get(event_type, (20, 50))'''

if OLD_FIND_START in src:
    src = src.replace(OLD_FIND_START, NEW_FIND_START, 1)
    print("[patch C-1] Added normalize_event_key() to find_event_window")
elif NEW_FIND_START in src:
    print("[skip C-1] normalize_event_key() already in find_event_window")
else:
    raise RuntimeError("Landmark not found: find_event_window signature")


# ===========================================================================
# (C-2) Rename event keys in map_all_events()
# ===========================================================================

OLD_MAP_ALL = '''    marriage = find_event_window("marriage", lagna, birth_year, ads)
    results["marriage"] = marriage
    marriage_start = marriage["start_year"] if marriage else birth_year + 22
    marriage_end   = marriage["end_year"]   if marriage else birth_year + 30

    results["foreign_move"] = find_event_window(
        "foreign_move", lagna, birth_year, ads
    )

    first_child = find_event_window(
        "first_child", lagna, birth_year, ads,
        after_year=marriage_start
    )
    results["first_child"] = first_child
    fc_start = first_child["start_year"] if first_child else marriage_end + 1
    fc_end   = first_child["end_year"]   if first_child else marriage_end + 4

    results["second_child"] = find_event_window(
        "second_child", lagna, birth_year, ads,
        after_year=fc_end + 1,   # must start at least 1 year after first child ends
        before_year=fc_end + 15, # up to 15 years after first child
    )

    results["divorce"] = find_event_window(
        "divorce", lagna, birth_year, ads,
        after_year=marriage_end + 3
    )'''

NEW_MAP_ALL = '''    marriage = find_event_window("serious_partnership_began", lagna, birth_year, ads)
    results["serious_partnership_began"] = marriage
    marriage_start = marriage["start_year"] if marriage else birth_year + 22
    marriage_end   = marriage["end_year"]   if marriage else birth_year + 30

    results["major_relocation"] = find_event_window(
        "major_relocation", lagna, birth_year, ads
    )

    first_child = find_event_window(
        "family_expansion_first", lagna, birth_year, ads,
        after_year=marriage_start
    )
    results["family_expansion_first"] = first_child
    fc_start = first_child["start_year"] if first_child else marriage_end + 1
    fc_end   = first_child["end_year"]   if first_child else marriage_end + 4

    results["family_expansion_second"] = find_event_window(
        "family_expansion_second", lagna, birth_year, ads,
        after_year=fc_end + 1,   # must start at least 1 year after first child ends
        before_year=fc_end + 15, # up to 15 years after first child
    )

    results["serious_partnership_ended"] = find_event_window(
        "serious_partnership_ended", lagna, birth_year, ads,
        after_year=marriage_end + 3
    )'''

if OLD_MAP_ALL in src:
    src = src.replace(OLD_MAP_ALL, NEW_MAP_ALL, 1)
    print("[patch C-2] Renamed event keys in map_all_events()")
elif NEW_MAP_ALL in src:
    print("[skip C-2] map_all_events() already patched")
else:
    raise RuntimeError("Landmark not found: map_all_events() event calls")


# ===========================================================================
# (C-3) Rename LABELS dict in format_for_prompt()
# ===========================================================================

OLD_LABELS = '''    LABELS = {
        "marriage":     "Marriage",
        "foreign_move": "Foreign relocation",
        "first_child":  "First child",
        "second_child": "Second child",
        "divorce":      "Divorce/separation",
    }'''

NEW_LABELS = '''    LABELS = {
        "serious_partnership_began":  "Serious partnership window",
        "major_relocation":           "Major relocation",
        "family_expansion_first":     "Family expansion (first)",
        "family_expansion_second":    "Family expansion (second)",
        "serious_partnership_ended":  "Partnership transition",
    }'''

if OLD_LABELS in src:
    src = src.replace(OLD_LABELS, NEW_LABELS, 1)
    print("[patch C-3] Renamed keys in format_for_prompt() LABELS dict")
elif NEW_LABELS in src:
    print("[skip C-3] format_for_prompt() LABELS already patched")
else:
    raise RuntimeError("Landmark not found: format_for_prompt() LABELS dict")


# ===========================================================================
# (C-4) Rename event keys in smoke tests
#        Test 1 RAMAN_ACTUAL
# ===========================================================================

OLD_RAMAN_ACTUAL = '''    RAMAN_ACTUAL = {
        "marriage":     1998,
        "foreign_move": 1992,
        "first_child":  2001,
        "second_child": 2003,
        "divorce":      2014,
    }'''

NEW_RAMAN_ACTUAL = '''    RAMAN_ACTUAL = {
        "serious_partnership_began":  1998,
        "major_relocation":           1992,
        "family_expansion_first":     2001,
        "family_expansion_second":    2003,
        "serious_partnership_ended":  2014,
    }'''

if OLD_RAMAN_ACTUAL in src:
    src = src.replace(OLD_RAMAN_ACTUAL, NEW_RAMAN_ACTUAL, 1)
    print("[patch C-4] Renamed RAMAN_ACTUAL keys in Test 1")
elif NEW_RAMAN_ACTUAL in src:
    print("[skip C-4] RAMAN_ACTUAL already patched")
else:
    raise RuntimeError("Landmark not found: RAMAN_ACTUAL dict")


# ===========================================================================
# (C-5) Rename event keys in Test 4 AT_ACTUALS
# ===========================================================================

OLD_AT_ACTUALS = '''    AT_ACTUALS = {
        "mother_death": 2000,
        "marriage":     2001,
        "first_child":  2005,
        "second_child": 2010,
    }'''

NEW_AT_ACTUALS = '''    AT_ACTUALS = {
        "loss_of_mother":             2000,
        "serious_partnership_began":  2001,
        "family_expansion_first":     2005,
        "family_expansion_second":    2010,
    }'''

if OLD_AT_ACTUALS in src:
    src = src.replace(OLD_AT_ACTUALS, NEW_AT_ACTUALS, 1)
    print("[patch C-5] Renamed AT_ACTUALS keys in Test 4")
elif NEW_AT_ACTUALS in src:
    print("[skip C-5] AT_ACTUALS already patched")
else:
    raise RuntimeError("Landmark not found: AT_ACTUALS dict")


# ===========================================================================
# (C-6) Rename event keys in Test 5 JS_ACTUALS
# ===========================================================================

OLD_JS_ACTUALS = '''    JS_ACTUALS = {
        "marriage":     2006,
        "foreign_move": 2007,
        "first_child":  2011,
        "second_child": 2013,
        "property":     2016,
    }'''

NEW_JS_ACTUALS = '''    JS_ACTUALS = {
        "serious_partnership_began":  2006,
        "major_relocation":           2007,
        "family_expansion_first":     2011,
        "family_expansion_second":    2013,
        "major_acquisition":          2016,
    }'''

if OLD_JS_ACTUALS in src:
    src = src.replace(OLD_JS_ACTUALS, NEW_JS_ACTUALS, 1)
    print("[patch C-6] Renamed JS_ACTUALS keys in Test 5")
elif NEW_JS_ACTUALS in src:
    print("[skip C-6] JS_ACTUALS already patched")
else:
    raise RuntimeError("Landmark not found: JS_ACTUALS dict")


# ===========================================================================
# (C-7) Rename property reference in Test 5 map
#        js_map["property"] = find_event_window("property", ...)
# ===========================================================================

OLD_JS_PROPERTY = '    js_map["property"] = find_event_window("property", "Aquarius", 1974, JS_ADS)'
NEW_JS_PROPERTY = '    js_map["major_acquisition"] = find_event_window("major_acquisition", "Aquarius", 1974, JS_ADS)'

if OLD_JS_PROPERTY in src:
    src = src.replace(OLD_JS_PROPERTY, NEW_JS_PROPERTY, 1)
    print("[patch C-7] Renamed js_map property line in Test 5")
elif NEW_JS_PROPERTY in src:
    print("[skip C-7] js_map property line already patched")
else:
    raise RuntimeError("Landmark not found: js_map property line in Test 5")


# ===========================================================================
# Write patched file
# ===========================================================================

with open(TARGET, "w") as f:
    f.write(src)

print(f"\n[done] Patched {TARGET}")
print("Run syntax check: python -c \"import ast; ast.parse(open('antar_engine/dasha_event_mapper.py').read())\"")
