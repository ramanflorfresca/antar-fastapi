"""
antar_engine/chart_identity.py

[chart-identity 2026-07-25] The "this is your chart" summary for the profile /
account surface: ascendant, Sun, Moon, the soul planet, the running dasha
chapter, and the strongest yogas — with a short plain-language reading.

This is the ONE surface where sign and planet names belong. Everywhere else the
product speaks in plain life-language (see the Today jargon gate); here the user
is looking AT their own chart and has asked to see it, so the vocabulary is the
point. The `reading` field still gives a plain paragraph for anyone who wants
the meaning without the terms.

Pure functions — no DB, no network — so they unit-test off a chart_data dict and
a vimsottari rows list. The route wires them to Supabase.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

# Sign each planet rules — for the plain "your rising sign is ruled by…" line.
_SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# One plain word per planet, for the reading line. No mechanics, no Sanskrit.
_PLANET_PLAIN = {
    "Sun": "identity and purpose", "Moon": "emotion and instinct",
    "Mars": "drive and courage", "Mercury": "mind and communication",
    "Jupiter": "growth and wisdom", "Venus": "love and value",
    "Saturn": "discipline and time", "Rahu": "ambition and the unfamiliar",
    "Ketu": "detachment and the past",
}

_ORDINAL = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th",
            7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}


def _planet(planets: Any, name: str) -> Dict[str, Any]:
    """A planet's placement dict from either storage format, or {}."""
    if isinstance(planets, dict):
        p = planets.get(name)
        return p if isinstance(p, dict) else {}
    if isinstance(planets, list):
        for p in planets:
            if isinstance(p, dict) and (p.get("name") or p.get("planet")) == name:
                return p
    return {}


def _placement(planets: Any, name: str) -> Optional[Dict[str, Any]]:
    p = _planet(planets, name)
    if not p or not p.get("sign"):
        return None
    return {
        "sign": p.get("sign"),
        "house": p.get("house"),
        "nakshatra": p.get("nakshatra"),
    }


def _parse_day(s: Any) -> Optional[date]:
    try:
        return datetime.fromisoformat(str(s)[:10]).date()
    except (ValueError, TypeError):
        return None


def _running_chapter(vim_rows: Any, today: date) -> Dict[str, Any]:
    """Current maha / antar / pratyantar lords + when the maha hands over,
    and which lord it hands over to. Any gap is simply omitted."""
    rows = vim_rows if isinstance(vim_rows, list) else []
    out: Dict[str, Any] = {}
    maha_end: Optional[date] = None

    def _lord(r):
        return r.get("lord_or_sign") or r.get("planet_or_sign")

    for r in rows:
        lvl = (r.get("level") or "").lower()
        sd = _parse_day(r.get("start_date") or r.get("start"))
        ed = _parse_day(r.get("end_date") or r.get("end"))
        if not (sd and ed and sd <= today <= ed):
            continue
        if lvl == "mahadasha":
            out["maha"] = _lord(r)
            out["maha_ends"] = ed.isoformat()
            maha_end = ed
        elif lvl in ("antardasha", "bhukti"):
            out["antar"] = _lord(r)
        elif lvl == "pratyantardasha":
            out["pratyantar"] = _lord(r)

    # The mahadasha that starts exactly when this one ends is the next chapter.
    if maha_end:
        for r in rows:
            if (r.get("level") or "").lower() != "mahadasha":
                continue
            if _parse_day(r.get("start_date") or r.get("start")) == maha_end:
                out["next_maha"] = _lord(r)
                break
    return out


def _reading(asc_sign, asc_lord, sun, moon, atma, chapter) -> str:
    """A short plain-language paragraph — the meaning without the mechanics."""
    bits: List[str] = []
    if asc_sign:
        lord_plain = _PLANET_PLAIN.get(asc_lord, "")
        line = f"You meet the world as {asc_sign}"
        if lord_plain:
            line += f", so {lord_plain} shapes how you show up"
        bits.append(line + ".")
    if sun and moon:
        bits.append(
            f"Your core self runs on {sun['sign']} while your inner world is "
            f"{moon['sign']} — how you act and how you feel are drawn from "
            f"different wells."
        )
    if atma and atma in _PLANET_PLAIN:
        bits.append(f"The thread your life keeps returning to is {_PLANET_PLAIN[atma]}.")
    if chapter.get("maha"):
        m = chapter["maha"]
        m_plain = _PLANET_PLAIN.get(m, "")
        line = f"Right now you are in a {m}"
        if m_plain:
            line += f" chapter — a long season about {m_plain}"
        if chapter.get("maha_ends"):
            line += f", and it closes on {chapter['maha_ends']}"
            if chapter.get("next_maha"):
                nxt = _PLANET_PLAIN.get(chapter["next_maha"], chapter["next_maha"])
                line += f", handing over to a {chapter['next_maha']} season of {nxt}"
        bits.append(line + ".")
    return " ".join(bits)


def build_chart_identity(chart_data: Any, vim_rows: Any = None,
                         name: str = "", today: Optional[date] = None) -> Dict[str, Any]:
    """{name, ascendant, sun, moon, atmakaraka, current_period, yogas, reading}.

    Returns {"available": False} only when the chart has no ascendant AND no
    Sun — i.e. it is not a real chart. Otherwise every present field is filled
    and missing ones are null, so a partial chart still renders.
    """
    cd = chart_data if isinstance(chart_data, dict) else {}
    today = today or date.today()

    lagna = cd.get("lagna") if isinstance(cd.get("lagna"), dict) else {}
    asc_sign = lagna.get("sign")
    asc_deg = lagna.get("degree")
    planets = cd.get("planets") or cd.get("planet_positions")

    sun = _placement(planets, "Sun")
    moon = _placement(planets, "Moon")

    if not asc_sign and not sun:
        return {"available": False}

    atma = cd.get("atmakaraka")
    if isinstance(atma, dict):
        atma = atma.get("planet") or atma.get("name")

    chapter = _running_chapter(vim_rows, today)
    asc_lord = _SIGN_LORD.get(asc_sign or "")

    # Top yogas, prose-safe: name + effect only, strongest first.
    yogas = []
    for y in (cd.get("yogas") or []):
        if isinstance(y, dict) and y.get("name"):
            yogas.append({"name": y.get("name"), "effect": y.get("effect", ""),
                          "strength": y.get("strength", "")})
    _rank = {"strong": 0, "moderate": 1, "weak": 2}
    yogas.sort(key=lambda y: _rank.get((y.get("strength") or "").lower(), 3))

    return {
        "available": True,
        "name": name or "",
        "ascendant": {
            "sign": asc_sign,
            "degree": round(asc_deg, 1) if isinstance(asc_deg, (int, float)) else None,
            "ruled_by": asc_lord,
        } if asc_sign else None,
        "sun": {**sun, "house_label": _ORDINAL.get(sun.get("house"))} if sun else None,
        "moon": {**moon, "house_label": _ORDINAL.get(moon.get("house"))} if moon else None,
        "atmakaraka": {"planet": atma, "means": _PLANET_PLAIN.get(atma, "")} if atma else None,
        "current_period": chapter or None,
        "yogas": yogas[:3],
        "reading": _reading(asc_sign, asc_lord, sun, moon, atma, chapter),
    }
