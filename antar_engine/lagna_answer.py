"""
antar_engine/lagna_answer.py
WHAT, HOW, WHEN, WHY — answered from the reference the question belongs to.

Three Jaimini references, each the correct origin for a different question:

    ARUDHA LAGNA   name, fame, reputation, standing — what the world SEES
    UPAPADA LAGNA  the marriage and the spouse
    SRI LAGNA      where prosperity settles

Every answer here carries four parts, because a reading that gives fewer is
either a compliment or a horoscope:

    WHAT   the kind of thing indicated
    HOW    the channel it arrives through
    WHEN   the period that switches it on — COMPUTED, never assumed
    WHY    the placement it rests on, named so the user can argue with it

WHEN IS THE PART THAT MAKES IT A CLAIM. The classical rule for a reference point
is that it fruits during the period of a planet sitting IN it, or of its lord.
That is a date, and a date can be wrong — which is the point. Without it, "you
have a strong image" is flattery that costs nothing.

Worked example from the chart this was built against: Sun, Rahu and Venus all
sit inside his Arudha Lagna, with Ketu opposing it. Three planets on the image
house is a great deal of recognition potential and Ketu opposite is why little
of it has arrived — Ketu severs what it faces. Rahu's eighteen-year mahadasha
begins 13 August 2026. The planet of scale and mass attention, sitting in his
house of image, starts its period in three weeks. That is a falsifiable claim
with a date on it, and it came out of the arithmetic rather than out of
encouragement.
"""

from typing import Dict, List, Optional

BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

# What each planet does to an IMAGE when it sits on the Arudha Lagna. The
# arudha is perception, so these are about how a person is read by others —
# not about their character.
IN_ARUDHA = {
    "Sun":     "authority — people assume you are the one in charge",
    "Moon":    "familiarity — people feel they know you, and warm to you quickly",
    "Mars":    "force — you are read as someone who pushes, and who wins arguments",
    "Mercury": "cleverness — you are read as the smartest person in the exchange",
    "Jupiter": "trust — people take your word as considered rather than casual",
    "Venus":   "appeal — people like you before they have decided why",
    "Saturn":  "gravity — recognition comes slowly and late, but does not leave",
    "Rahu":    "scale — attention arrives suddenly and in volume, often from strangers",
    "Ketu":    "invisibility — you are underestimated, and often prefer it that way",
}

OPPOSING_ARUDHA = {
    "Ketu":   "Ketu sits opposite your image and cuts at it. Recognition you have "
              "earned tends not to stick, and part of you does not chase it.",
    "Saturn": "Saturn sits opposite your image and slows it. Recognition is "
              "delayed rather than denied.",
    "Rahu":   "Rahu sits opposite your image — how you are seen keeps being "
              "rewritten by other people's stories about you.",
    "Mars":   "Mars sits opposite your image — you attract argument as easily as "
              "attention.",
}


def _occ(chart: dict, sign_idx: int) -> List[str]:
    from antar_engine.special_lagnas import _occupants_of_sign
    return _occupants_of_sign(chart, sign_idx)


def _when_planet_runs(dashas: Optional[dict], planet: str) -> Optional[Dict]:
    """The next period belonging to `planet`, at the largest available level.

    Answers WHEN with a date rather than a mood. Returns the soonest mahadasha
    or antardasha that has not yet ended.
    """
    if not dashas or not planet:
        return None
    from datetime import date
    today = date.today().isoformat()
    best = None
    for r in (dashas.get("vimsottari") or []):
        if not isinstance(r, dict):
            continue
        lord = r.get("lord_or_sign") or r.get("planet_or_sign")
        if lord != planet:
            continue
        lvl = str(r.get("level") or "").lower()
        if lvl not in ("mahadasha", "antardasha"):
            continue
        start = str(r.get("start_date") or "")[:10]
        end = str(r.get("end_date") or "")[:10]
        if not end or end < today:
            continue
        rank = 0 if lvl == "mahadasha" else 1
        cand = {"level": lvl, "start": start, "end": end, "rank": rank,
                "running": start <= today <= end}
        if best is None or (cand["running"], -rank, -_neg(start)) > \
                           (best["running"], -best["rank"], -_neg(best["start"])):
            best = cand
    return best


def _neg(iso: str) -> int:
    try:
        return int(iso.replace("-", ""))
    except Exception:
        return 99999999


def name_and_fame(chart: dict, dashas: Optional[dict] = None) -> Dict:
    """WHAT / HOW / WHEN / WHY for recognition, read from the Arudha Lagna."""
    from antar_engine.special_lagnas import all_references
    refs = all_references(chart)
    al = refs.get("arudha")
    if not al:
        return {"available": False}

    base = al["sign_index"]
    inside = _occ(chart, base)
    opposite = _occ(chart, (base + 6) % 12)
    what, why, when_lines = [], [], []

    # WHAT — the flavour of recognition, from what sits on the image house.
    if inside:
        for p in inside:
            if p in IN_ARUDHA:
                what.append(f"{p} in your image house: {IN_ARUDHA[p]}.")
        if len(inside) >= 3:
            why.append(f"Three planets sit in your Arudha Lagna ({al['sign']}) — "
                       f"{', '.join(inside)}. That is a crowded image house: a great "
                       f"deal of recognition is available, and it is not subtle.")
        else:
            why.append(f"{', '.join(inside)} in your Arudha Lagna ({al['sign']}).")
    else:
        what.append(f"Your image house is empty, so how you are seen follows its "
                    f"lord {al['lord']} rather than any planet sitting there.")

    # The counterweight. This is why recognition has or has not arrived.
    for p in opposite:
        if p in OPPOSING_ARUDHA:
            why.append(OPPOSING_ARUDHA[p])

    # WHEN — the period of a planet IN the arudha, or of its lord. Classical,
    # and it produces a date.
    candidates = list(inside) + ([al["lord"]] if al["lord"] not in inside else [])
    timed = []
    for p in candidates:
        w = _when_planet_runs(dashas, p)
        if w:
            timed.append((p, w))
    timed.sort(key=lambda x: (not x[1]["running"], x[1]["rank"], x[1]["start"]))
    for p, w in timed[:3]:
        if w["running"]:
            when_lines.append(f"{p}'s {w['level']} is running now and ends {w['end']} "
                              f"— this window is already open.")
        else:
            when_lines.append(f"{p}'s {w['level']} runs {w['start']} to {w['end']}.")
    if not when_lines:
        when_lines.append("No period belonging to your image house is on record ahead — "
                          "recognition here builds steadily rather than in a burst.")

    how = []
    lord_house = ((chart.get("planets") or {}).get(al["lord"]) or {}).get("house")
    if lord_house:
        how.append(f"Your image is carried by {al['lord']}, placed in your "
                   f"{_ord(lord_house)} house — that is the arena it works through.")

    return {
        "available": True,
        "reference": "arudha",
        "arudha_sign": al["sign"],
        "arudha_house": al["house"],
        "occupants": inside,
        "opposing": opposite,
        "what": what, "how": how, "when": when_lines, "why": why,
    }


def _ord(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


# Which reference a question belongs to. Deliberately small: a router that
# claims to handle everything handles nothing.
QUESTION_REFERENCE = {
    "fame": "arudha", "name": "arudha", "reputation": "arudha",
    "recognition": "arudha", "image": "arudha", "status": "arudha",
    "marriage": "upapada", "spouse": "upapada", "divorce": "upapada",
    "wealth": "sri", "money": "sri", "prosperity": "sri",
}


def answer_from_reference(chart: dict, topic: str,
                          dashas: Optional[dict] = None) -> Dict:
    """Route a topic to its reference and answer in four parts."""
    ref = QUESTION_REFERENCE.get((topic or "").strip().lower())
    if ref == "arudha":
        return name_and_fame(chart, dashas)
    if ref == "sri":
        try:
            from antar_engine.wealth_channel import wealth_channel
            w = wealth_channel(chart, dashas)
            if not w.get("available"):
                return {"available": False}
            return {"available": True, "reference": "sri",
                    "what": [w["lines"][0]], "how": w["lines"][2:3],
                    "when": w["timing"]["lines"], "why": w["lines"][1:2]}
        except Exception:
            return {"available": False}
    if ref == "upapada":
        try:
            from antar_engine.special_lagnas import read_from
            r = read_from(chart, "upapada")
            if not r.get("available"):
                return {"available": False}
            return {"available": True, "reference": "upapada",
                    "what": [f"The marriage is read from the Upapada in {r['sign']}, "
                             f"your {_ord(r['house_from_lagna'])} house."],
                    "how": [], "when": [], "why": r["findings"]}
        except Exception:
            return {"available": False}
    return {"available": False}
