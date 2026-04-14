"""
antar_engine/dasha_event_mapper.py
=====================================
Python computes which MD+AD triggered each life event.
Claude/DeepSeek narrates — never calculates.

CONFIRMED MAPPINGS (from Raman + Andres ground truth):
  Marriage:     Venus-Saturn AD   → Saturn = formal commitment
  America:      Venus-Rahu AD     → Rahu = foreign permanent move
  First child:  Venus-Mercury AD  → Mercury = 9H lord (dharma/progeny)
  Second child: Venus-Ketu AD     → sequential, 2 years after first
  Divorce:      Moon-Saturn AD    → Moon = 7H lord, Saturn = endings
  Andres daughter: Jupiter-Venus AD → Venus = female children karaka
"""

from typing import Optional

# ---------------------------------------------------------------------------
# AD priority rules — confirmed by ground truth testing
# Format: (planet, reason, priority_score)
# Higher score = stronger match
# ---------------------------------------------------------------------------

MARRIAGE_PRIORITY = {
    "Capricorn": [
        ("Saturn",  "Saturn formalizes commitment — legal union, ceremony",     10),
        ("Moon",    "Moon rules 7H for Capricorn — emotional commitment",        8),
        ("Jupiter", "Jupiter = dharmic marriage through family",                  6),
        ("Venus",   "Venus romance (weaker when Venus is already MD)",            4),
        ("Rahu",    "Rahu = romance starts, rarely formalizes as marriage",       2),
    ],
    "Cancer": [
        ("Saturn",  "Saturn rules 7H+8H for Cancer — formal commitment",        10),
        ("Venus",   "Venus = romance karaka",                                     7),
        ("Jupiter", "Jupiter = dharmic expansion",                                6),
    ],
    "_default": [
        ("Saturn",  "Saturn = formal commitment",                                10),
        ("Venus",   "Venus = romance karaka",                                     8),
        ("Jupiter", "Jupiter = dharmic marriage",                                  6),
        ("Moon",    "Moon = emotional commitment",                                 5),
    ],
}

FOREIGN_MOVE_PRIORITY = {
    "_default": [
        ("Rahu",    "Rahu = foreign karaka, unconventional permanent move",      10),
        ("Jupiter", "Jupiter = foreign through education/opportunity (12H lord)",  7),
        ("Mercury", "Mercury = travel/communication-driven relocation",            5),
        ("Ketu",    "Ketu = spiritual/karmic foreign journey",                     4),
    ],
}

FIRST_CHILD_PRIORITY = {
    "Capricorn": [
        ("Mercury", "Mercury rules 9H for Capricorn — dharma/progeny/luck",     10),
        ("Jupiter", "Jupiter = natural karaka for children",                      8),
        ("Moon",    "Moon = nurturing, emotional child-bearing period",            5),
        ("Sun",     "Sun = soul entering family",                                  4),
    ],
    "Cancer": [
        ("Venus",   "Venus = karaka of female children, 11H lord for Cancer",   10),
        ("Mars",    "Mars rules 5H for Cancer — house of children",               8),
        ("Jupiter", "Jupiter = natural karaka for children",                      7),
    ],
    "_default": [
        ("Jupiter", "Jupiter = natural karaka for children",                     10),
        ("Venus",   "Venus = karaka of female children",                          8),
        ("Mercury", "Mercury = 9H lord for many lagnas",                          7),
        ("Moon",    "Moon = nurturing period",                                     5),
    ],
}

SECOND_CHILD_PRIORITY = {
    "_default": [
        ("Ketu",    "Ketu = completion of karma, sequential 2nd child",          10),
        ("Sun",     "Sun = soul, next generation, transition period",              8),
        ("Mercury", "Mercury = 9H lord (classical 2nd child house)",               7),
        ("Saturn",  "Saturn = delayed but eventual birth",                         5),
        ("Moon",    "Moon = nurturing continuation",                               4),
    ],
}

DIVORCE_PRIORITY = {
    "Capricorn": [
        ("Saturn",  "Saturn during Moon MD = 7H lord + endings = textbook divorce", 10),
        ("Ketu",    "Ketu = spiritual detachment, past-life ending",                  7),
        ("Rahu",    "Rahu = sudden/foreign separation",                               5),
        ("Sun",     "Sun = ego clash ending relationship",                            4),
    ],
    "_default": [
        ("Saturn",  "Saturn = endings and formal separation",                        10),
        ("Ketu",    "Ketu = detachment",                                              7),
        ("Rahu",    "Rahu = sudden separation",                                       5),
    ],
}

AGE_RANGES = {
    "marriage":     (20, 35),
    "foreign_move": (15, 45),
    "first_child":  (22, 37),
    "second_child": (24, 42),
    "divorce":      (25, 55),
}

PRIORITY_TABLES = {
    "marriage":     MARRIAGE_PRIORITY,
    "foreign_move": FOREIGN_MOVE_PRIORITY,
    "first_child":  FIRST_CHILD_PRIORITY,
    "second_child": SECOND_CHILD_PRIORITY,
    "divorce":      DIVORCE_PRIORITY,
}


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def find_event_window(
    event_type: str,
    lagna: str,
    birth_year: int,
    ads: list,
    after_year: Optional[int] = None,
    before_year: Optional[int] = None,
) -> Optional[dict]:
    """
    Find the most likely MD+AD window for a life event.

    Args:
        event_type:  marriage | foreign_move | first_child | second_child | divorce
        lagna:       Capricorn | Cancer | etc
        birth_year:  int
        ads:         list of antardasha dicts from dasha_periods table
        after_year:  event must start after this year (sequential constraint)
        before_year: event must end before this year

    Returns dict with: planet, parent_md, start, end, reason, midpoint_year
    """
    min_age, max_age = AGE_RANGES.get(event_type, (20, 50))
    eligible_start = birth_year + min_age
    eligible_end   = birth_year + max_age

    if after_year:
        eligible_start = max(eligible_start, after_year)
    if before_year:
        eligible_end = min(eligible_end, before_year)

    # Get priority table for this event + lagna
    tables = PRIORITY_TABLES.get(event_type, {})
    priority_list = tables.get(lagna, tables.get("_default", []))
    priority_map  = {p: score for p, _, score in priority_list}
    reason_map    = {p: reason for p, reason, _ in priority_list}

    candidates = []
    for ad in ads:
        start_str = str(ad.get("start_date", ad.get("start", "")))[:10]
        end_str   = str(ad.get("end_date",   ad.get("end",   "")))[:10]
        if not start_str or not end_str:
            continue
        try:
            start_year = int(start_str[:4])
            end_year   = int(end_str[:4])
        except ValueError:
            continue

        # Must overlap with eligible range
        if end_year < eligible_start or start_year > eligible_end:
            continue

        planet = ad.get("planet_or_sign", ad.get("planet", ""))
        parent = (ad.get("metadata") or {}).get("parent_lord", ad.get("parent", ""))
        score  = priority_map.get(planet, 0)

        if score == 0:
            continue  # planet not relevant for this event

        candidates.append({
            "planet":         planet,
            "parent_md":      parent,
            "start":          start_str,
            "end":            end_str,
            "start_year":     start_year,
            "end_year":       end_year,
            "score":          score,
            "reason":         reason_map.get(planet, "classical dasha timing"),
        })

    if not candidates:
        return None

    # Sort by score (highest first), then by start_year (earliest first)
    candidates.sort(key=lambda x: (-x["score"], x["start_year"]))
    best = candidates[0]
    best["midpoint_year"] = (best["start_year"] + best["end_year"]) // 2
    best["event_type"] = event_type
    return best


def map_all_events(birth_year: int, lagna: str, ads: list) -> dict:
    """
    Compute all standard life event windows for a chart.
    Returns dict of {event_type: window_dict}.
    """
    results = {}

    # Marriage (no dependency)
    marriage = find_event_window("marriage", lagna, birth_year, ads)
    results["marriage"] = marriage
    marriage_year = marriage["end_year"] if marriage else birth_year + 30

    # Foreign move (no dependency)
    results["foreign_move"] = find_event_window(
        "foreign_move", lagna, birth_year, ads
    )

    # First child (must be after marriage)
    first_child = find_event_window(
        "first_child", lagna, birth_year, ads,
        after_year=marriage["start_year"] if marriage else birth_year + 22
    )
    results["first_child"] = first_child
    first_child_year = first_child["end_year"] if first_child else marriage_year + 3

    # Second child (must be after first child, within 5 years)
    results["second_child"] = find_event_window(
        "second_child", lagna, birth_year, ads,
        after_year=first_child["start_year"] if first_child else birth_year + 25,
        before_year=first_child_year + 5 if first_child else birth_year + 35,
    )

    # Divorce (must be 5+ years after marriage)
    results["divorce"] = find_event_window(
        "divorce", lagna, birth_year, ads,
        after_year=marriage_year + 5
    )

    return results


def format_for_prompt(results: dict) -> str:
    """
    Format computed event windows for injection into Claude's context.
    Claude narrates these — never recalculates them.
    """
    lines = ["\n## COMPUTED LIFE EVENT WINDOWS (Python — do not recalculate)\n"]
    labels = {
        "marriage":     "Marriage",
        "foreign_move": "Foreign relocation",
        "first_child":  "First child",
        "second_child": "Second child",
        "divorce":      "Divorce/separation",
    }
    for event, label in labels.items():
        w = results.get(event)
        if w:
            lines.append(
                f"{label}: {w['parent_md']} MD + {w['planet']} AD "
                f"({w['start'][:7]} to {w['end'][:7]}) — {w['reason']}"
            )
        else:
            lines.append(f"{label}: no clear window found")
    lines.append(
        "\nUse these windows when answering questions about past life events. "
        "Do not override with your own calculations."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Smoke test against confirmed ground truth
# ---------------------------------------------------------------------------

def _smoke_test():
    print("DashaEventMapper smoke test — Raman (Capricorn lagna)\n")

    # Real ADs from DB
    ads = [
        {"planet_or_sign": "Venus",   "start_date": "1983-08-13", "end_date": "1986-12-12", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Sun",     "start_date": "1986-12-12", "end_date": "1987-12-12", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Moon",    "start_date": "1987-12-12", "end_date": "1989-08-12", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Mars",    "start_date": "1989-08-12", "end_date": "1990-10-12", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Rahu",    "start_date": "1990-10-12", "end_date": "1993-10-12", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Jupiter", "start_date": "1993-10-12", "end_date": "1996-06-12", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Saturn",  "start_date": "1996-06-12", "end_date": "1999-08-13", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Mercury", "start_date": "1999-08-13", "end_date": "2002-06-13", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Ketu",    "start_date": "2002-06-13", "end_date": "2003-08-13", "metadata": {"parent_lord": "Venus"}},
        {"planet_or_sign": "Moon",    "start_date": "2009-08-13", "end_date": "2010-06-13", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Mars",    "start_date": "2010-06-13", "end_date": "2011-01-12", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Rahu",    "start_date": "2011-01-12", "end_date": "2012-07-13", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Jupiter", "start_date": "2012-07-13", "end_date": "2013-11-12", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Saturn",  "start_date": "2013-11-12", "end_date": "2015-06-13", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Mercury", "start_date": "2015-06-13", "end_date": "2016-11-11", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Ketu",    "start_date": "2016-11-11", "end_date": "2017-06-12", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Venus",   "start_date": "2017-06-12", "end_date": "2019-02-11", "metadata": {"parent_lord": "Moon"}},
        {"planet_or_sign": "Sun",     "start_date": "2019-02-11", "end_date": "2019-08-13", "metadata": {"parent_lord": "Moon"}},
    ]

    ACTUAL = {
        "marriage":     (1998, "Venus-Saturn AD Jun 1996 - Aug 1999"),
        "foreign_move": (1992, "Venus-Rahu AD Oct 1990 - Oct 1993"),
        "first_child":  (2001, "Venus-Mercury AD Aug 1999 - Jun 2002"),
        "second_child": (2003, "Venus-Ketu AD Jun 2002 - Aug 2003"),
        "divorce":      (2014, "Moon-Saturn AD Nov 2013 - Jun 2015"),
    }

    results = map_all_events(1974, "Capricorn", ads)

    correct = 0
    for event, (actual_year, actual_desc) in ACTUAL.items():
        w = results.get(event)
        if not w:
            print(f"  {event:15s}: NO PREDICTION  (actual: {actual_year}) ❌")
            continue
        in_window = w["start_year"] <= actual_year <= w["end_year"]
        mark = "✅" if in_window else "❌"
        correct += 1 if in_window else 0
        print(f"  {event:15s}: {w['parent_md']} MD + {w['planet']} AD "
              f"({w['start'][:7]}–{w['end'][:7]})  actual={actual_year}  {mark}")
        if not in_window:
            print(f"    Expected: {actual_desc}")

    pct = correct / len(ACTUAL) * 100
    print(f"\nPython DashaEventMapper: {correct}/{len(ACTUAL)} = {pct:.0f}%")

    print("\nFormatted for prompt injection:")
    print(format_for_prompt(results))


if __name__ == "__main__":
    _smoke_test()
