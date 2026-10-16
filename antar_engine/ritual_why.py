"""[ritual-why 2026-10-15] The plain reason behind each Rituals card, so nothing reads as hardcoded: what is happening
today, why this answers it, and how it changes from day to day. Wording is owner-editable in data/ritual_why.json
(no planet, book or method names); the cause comes from the same chart reads the cards already use."""
import json
import os
import re
from typing import Optional

_PATH = os.path.join(os.path.dirname(__file__), "data", "ritual_why.json")
_CACHE: dict = {}


def _data() -> dict:
    if not _CACHE:
        try:
            with open(_PATH, encoding="utf-8") as fh:
                _CACHE.update(json.load(fh))
        except Exception as e:
            print(f"[ritual-why] data unavailable: {e}")
            _CACHE["_empty"] = True
    return _CACHE


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _dot(s: str) -> str:
    return s if s.endswith((".", "!", "?")) else s + "."


def food_why(food: dict) -> Optional[dict]:
    """What the day is doing to the body, why this food answers it, what adds to it, and how it changes."""
    d = _data()
    f = food or {}
    mode = f.get("mode")
    out = {}
    if mode == "strengthen":
        feeds = (f.get("why_eat") or "").strip()
        if feeds:
            out["state_plain"] = _dot(feeds)
        out["adds_plain"] = d.get("food_strengthen_adds_plain")
    else:
        try:
            from antar_engine.ayurveda_astrology import PLANET_DOSHA
            dosha = (PLANET_DOSHA.get(f.get("planet")) or {}).get("dosha")
        except Exception:
            dosha = None
        row = (d.get("food_state") or {}).get(dosha)
        if not row:
            return None
        out.update(row)
    out["variation_plain"] = d.get("food_variation_plain")
    return {k: v for k, v in out.items() if v}


def verse_why(wisdom: dict) -> Optional[dict]:
    """Why this theme today (the real cause), what the verse is about, and how it differs on other days."""
    w = wisdom or {}
    season = w.get("season")
    if not season:
        return None
    d = _data()
    out = {}
    try:
        from antar_engine.daily_wisdom import cause_sentence
        c = cause_sentence(season, w.get("season_cause"), "en")
        if c:
            out["cause_plain"] = _cap(_dot(c))
    except Exception as e:
        print(f"[ritual-why] cause skipped: {e}")
    themes = [t.replace("_", " ") for t in ((w.get("verse") or {}).get("themes") or [])][:3]
    if themes:
        out["about_plain"] = "It is paired with a verse about " + ", ".join(themes[:-1]) + (" and " if len(themes) > 1 else "") + themes[-1] + "."
    out["variation_plain"] = d.get("verse_variation_plain")
    return {k: v for k, v in out.items() if v}


def mantra_why(planet: Optional[str], purpose: Optional[str] = None) -> Optional[dict]:
    """The area it supports today, what repeating it does, and why it changes."""
    d = _data()
    out = {}
    area = (d.get("planet_area") or {}).get(str(planet or "").title())
    if area:
        out["supports_plain"] = f"Today it supports {area}."
    out["mechanism_plain"] = d.get("mantra_mechanism_plain")
    out["variation_plain"] = d.get("mantra_variation_plain")
    return {k: v for k, v in out.items() if v} or None


def chant_for(remedy_title: str) -> Optional[dict]:
    """A chant block for a remedy that names a known chant. Play only appears when its audio file is uploaded."""
    d = _data()
    for c in d.get("chants") or []:
        if re.search(c["match"], remedy_title or "", re.I):
            out = {"key": c["key"], "name": c["name"], "how_plain": c.get("how_plain")}
            if c["key"] == "gayatri":
                try:
                    from antar_engine.daily_wisdom import MANTRAS
                    m = MANTRAS["steady"]
                    out["sanskrit"], out["transliteration"] = m["sanskrit"], m["transliteration"]
                except Exception:
                    pass
            a = c.get("audio")
            if a and a in (d.get("audio_available") or []):
                from antar_engine.practice_library import AUDIO_BASE
                out["audio_url"] = f"{AUDIO_BASE}/{a}.mp3"
                out["audio_credit_plain"] = c.get("audio_credit_plain")
            return {k: v for k, v in out.items() if v}
    return None


def chants_for_actives(actives: list) -> list:
    """Chants offered because an area of the chart is under strain right now: [{title, key, planet, days, why_plain}],
    strongest strain first. `actives` is the practice engine's merged active areas (planet + severity)."""
    d = _data()
    best = {}
    for a in actives or []:
        p, sev = str(a.get("planet") or "").title(), float(a.get("severity") or 0)
        if p and sev > best.get(p, -1):
            best[p] = sev
    out = []
    for c in d.get("chants") or []:
        hit = [p for p in (c.get("planets") or []) if p in best]
        if not hit or not c.get("title"):
            continue
        p = max(hit, key=lambda x: best[x])
        area = (d.get("planet_area") or {}).get(p)
        out.append({"title": c["title"], "key": c["key"], "planet": p, "sev": best[p], "days": c.get("days") or [],
                    "why_plain": (f"This is offered because {area} is asking for support right now." if area else None)})
    out.sort(key=lambda x: -x["sev"])
    return out
