"""[day-paragraph 2026-10-15] The Today-detail area lines as 3-4 sentence paragraphs. Built ONLY from what the day already says
(its day-map line and move) plus how that area reads for the month (the same month read the sheet shows) and the day's own
best / steer-clear clock window. Nothing is invented; wording lives in data/day_paragraph.json."""
import json
import os
from typing import List, Optional

_PATH = os.path.join(os.path.dirname(__file__), "data", "day_paragraph.json")
_CACHE: dict = {}
# day-map area -> month area read
MONTH_OF = {"work": "career", "authority": "career", "money": "money", "speculation": "money", "relationship": "love",
            "family": "love", "health": "health", "home": "health", "spiritual": "mind"}


def _data() -> dict:
    if not _CACHE:
        try:
            with open(_PATH, encoding="utf-8") as fh:
                _CACHE.update(json.load(fh))
        except Exception as e:
            print(f"[day-paragraph] data unavailable: {e}")
            _CACHE["_empty"] = True
    return _CACHE


def _dot(s: str) -> str:
    s = (s or "").strip()
    return s if not s or s.endswith((".", "!", "?")) else s + "."


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _band_move(key: str, line: str) -> Optional[str]:
    """The micro-move for the band this line was written from, when the line does not already carry it."""
    try:
        from antar_engine import daily_life_areas as dla
        cells = [c for c in (dla._LINES.get(key) or {}).values()]
        for stage in dla._LINES_NOJOB.values():
            cells += list((stage.get(key) or {}).values())
        for c in cells:
            if c.get("line") and c["line"] in line:
                mv = (c.get("move") or "").strip()
                return None if (not mv or mv.lower().rstrip(".") in line.lower()) else _cap(_dot(mv))
    except Exception:
        pass
    return None


def paragraphs(day_map: list, month_domains: Optional[list], window: Optional[dict], lang: str = "en") -> List[dict]:
    """[{key, label, tone, paragraph}] in the day map's own order."""
    d = _data().get(lang) or _data().get("en")
    if not d:
        return []
    month = {m.get("key"): m for m in (month_domains or [])}
    # the SAME one best / one avoid window Home's "Today's read" already states (today_decision), never a second set of times
    best = ((window or {}).get("best") or "").strip() or None
    avoid = ((window or {}).get("avoid") or "").strip() or None
    out, used_best, used_avoid = [], False, False
    for e in day_map or []:
        line = (e.get("line") or "").strip()
        if not line:
            continue
        tone = e.get("tone") or "neutral"
        tone_k = tone if tone in ("opportunity", "risk") else "neutral"
        parts = [_dot(line)]
        mv = _band_move(e.get("key"), line)
        if mv:
            parts.append(mv)
        m = month.get(MONTH_OF.get(e.get("key")))
        if m and m.get("verdict") in ("good", "steady", "tough"):
            tpl = (d["context"].get(tone_k) or {}).get(m["verdict"])
            if tpl:
                parts.append(tpl.format(area=(m.get("label") or e.get("label") or "").lower()))
        if tone_k == "opportunity" and best and not used_best:
            parts.append(d["best_window"].format(window=best))
            used_best = True
        elif tone_k == "risk" and avoid and not used_avoid:
            parts.append(d["avoid_window"].format(window=avoid))
            used_avoid = True
        out.append({"key": e.get("key"), "label": e.get("label"), "tone": tone, "paragraph": " ".join(parts)})
    return out
