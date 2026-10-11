"""[do-dont-why 2026-10-11] A plain reason for each Do / Avoid line on the daily card.

Each line comes from one of the day's active areas (house_activation sweep: key, label, say, polarity, drivers, houses) via
_DAILY_DO_DONT_BY_DOMAIN. The card showed the line with no reason. The reason is read from the SAME area's drivers — the
running Vimśottarī lord, the houses today's transits touch, the Jaimini chara period — nothing new is inferred.
English; the daily-signal translation layer localises it with the other do/dont strings."""
from __future__ import annotations

import re

_ORD = {1: "1st", 2: "2nd", 3: "3rd"}


def _o(n: int) -> str:
    return _ORD.get(n, f"{n}th")


def _join(items: list) -> str:
    items = [x for x in items if x]
    return items[0] if len(items) == 1 else (", ".join(items[:-1]) + " and " + items[-1] if items else "")


def _cause(area: dict) -> str:
    parts = []
    lord = None
    houses = []
    jaimini = bool(area.get("jaimini"))
    for d in (area.get("drivers") or []):
        m = re.search(r"Vim\S*\s+(\w+) activates it", str(d))
        if m and not lord:
            lord = m.group(1)
        m = re.search(r"houses \[([\d, ]+)\]", str(d))
        if m and not houses:
            houses = [int(x) for x in re.findall(r"\d+", m.group(1))]
        if "Jaimini" in str(d):
            jaimini = True
    if lord:
        parts.append(f"your running {lord} period activates it")
    if houses:
        parts.append(f"today's transits are touching your {_join([_o(h) for h in houses[:3]])} house{'s' if len(houses) > 1 else ''}")
    if jaimini and not lord:
        parts.append("your Jaimini (chara) period also points here")
    return " and ".join(parts)


def area_why(area: dict, kind: str) -> str:
    """kind: "do" (an opportunity area) or "dont" (a risk / caution area). "" when the area has nothing to cite."""
    try:
        say = (area.get("say") or area.get("label") or "").strip()
        cause = _cause(area)
        if not say or not cause:
            return ""
        say = say[:1].upper() + say[1:]
        if kind == "do":
            return f"{say} is switched on today — {cause}."
        return f"{say} is under pressure today — {cause}, and the timing runs against it."
    except Exception:
        return ""
