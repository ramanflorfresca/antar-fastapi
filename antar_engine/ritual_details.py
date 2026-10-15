"""
Specific, plain-language details for the Rituals cards: how and when to do a remedy, why a colour and where to wear it, why each
food. Deterministic: the remedy how-to text lives in data/ritual_remedy_details.json (owner-editable); colour and food details
come from the engines' own fields (the daily colour and food blocks). No method, book or planet names reach the user: every string
passes `clean` before it is returned, and an item that would leak is dropped, never shown.
"""
import json
import os
import re
from datetime import date as _date
from typing import Optional

from antar_engine import meanings as M
from antar_engine.ritual_today import _BANNED, _DAYNAME, clean

_PATH = os.path.join(os.path.dirname(__file__), "data", "ritual_remedy_details.json")
_WEEKDAY_PLANET = {"Monday": "Moon", "Tuesday": "Mars", "Wednesday": "Mercury", "Thursday": "Jupiter",
                   "Friday": "Venus", "Saturday": "Saturn", "Sunday": "Sun"}
_TABLE = None


def _table() -> list:
    global _TABLE
    if _TABLE is None:
        try:
            with open(_PATH, encoding="utf-8") as fh:
                _TABLE = json.load(fh).get("remedies") or []
        except Exception:
            _TABLE = []
    return _TABLE


def covers_of(planet: Optional[str]) -> Optional[str]:
    """What a planet stands for, in plain words (first clause), or None."""
    b = M.planet(planet, "en") if planet else None
    c = (b or {}).get("covers")
    return clean(c.split(";")[0].strip()) if c else None


def _andlist(txt: Optional[str]) -> Optional[str]:
    """"thinking, speaking, trading, learning" -> "your thinking, speaking, trading and learning"."""
    if not txt:
        return None
    parts = [x.strip() for x in txt.split(",") if x.strip()]
    if not parts:
        return None
    body = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return "your " + body


def remedy_why(text: str) -> Optional[str]:
    """One specific sentence on why this remedy: the part of life its day stands for. None when the remedy names no day."""
    day = _weekday_in(text)
    cov = _andlist(covers_of(_WEEKDAY_PLANET.get(day))) if day else None
    if not cov:
        return None
    return clean(f"Your year's remedies ask for this. {day}s stand for {cov}, and keeping this steady helps those hold.")


def _weekday_in(text: str) -> Optional[str]:
    return next((d for d in _DAYNAME if re.search(r"(?i)\b" + d[:3] + r"[a-z]*\b", text or "")), None)


def remedy_details(text: str, today: Optional[_date] = None) -> dict:
    """{how_plain, when_plain, how_long_plain, for_plain, safety_plain} for a remedy sentence; keys with nothing sound are omitted."""
    t = text or ""
    day = _weekday_in(t)
    covers = covers_of(_WEEKDAY_PLANET.get(day)) if day else None
    for row in _table():
        if not re.search(row["match"], t, re.I):
            continue
        out = {}
        for k in ("how_plain", "when_plain", "how_long_plain", "for_plain", "safety_plain"):
            v = row.get(k)
            if not v:
                continue
            if "{day}" in v and not day:
                continue
            if "{covers}" in v and not covers:
                continue
            v = v.replace("{day_or_any}", day or "Any day").replace("{day}", day or "").replace("{covers}", _andlist(covers) or "")
            v = clean(v.strip())
            if v:
                out[k] = v
        return out
    return {}


def colour_details(col: Optional[dict], daily_color: dict, skip: list, refused_texts: list) -> dict:
    """Where to wear today's colour, what it supports, the support colour and why each skipped colour is skipped."""
    out = {}
    if col:
        planet = ((col.get("basis") or "").split(":") + [None])[1]
        sup = covers_of(planet.capitalize() if planet else None)
        if sup and col.get("scope") == "day":
            out["supports_plain"] = clean(f"{col['name']} supports {_andlist(sup)} today.")
        out["where_plain"] = "Wear it where it is seen or touches you: a shirt, scarf, tie or bag. A small piece is enough if the outfit does not allow it."
    ds = (daily_color or {})
    sup2 = (ds.get("support") or "").split("/")[0].strip().lower()
    if clean(ds.get("support")) and sup2 and (not col or sup2 not in col["name"].lower()):
        out["support_colour_plain"] = clean(f"If you want a second colour, add {sup2}.")
    reasons = []
    for s in skip or []:
        nm = s.get("name", "")
        hit = next((t for t in (refused_texts or []) if re.search(r"(?i)\b" + re.escape(nm.split()[-1]) + r"\b", t)), None)
        r = (f"Your year's remedies say to refuse {nm.lower()} this year." if hit
             else f"{nm} does not suit your chart right now, so leave it for today.")
        reasons.append({"name": nm, "hex": s.get("hex"), "why_plain": r})
    if reasons:
        out["skip_reasons"] = reasons
    return {k: v for k, v in out.items() if v}


def food_details(f: dict, today: Optional[_date] = None) -> dict:
    """The food block's own specifics: herb, why to avoid, how long to keep it up, its best day."""
    f = f or {}
    out = {}
    if clean(f.get("herb")):
        out["herb_plain"] = clean(f"A herb that goes with this: {f['herb']}.")
    wa = clean(f.get("why_avoid"))
    if wa:
        out["why_avoid_plain"] = wa[:1].upper() + wa[1:] + ("" if wa.endswith(".") else ".")
    if clean(f.get("duration")):
        out["repeat_plain"] = clean(f["duration"]) if str(f["duration"]).endswith(".") else clean(f["duration"]) + "."
    best = clean(f.get("best_day"))
    if best and not f.get("is_best_day"):
        out["best_day_plain"] = f"Works best on {best}s."
    return out
