"""[area-paragraph 2026-10-15] A 2-3 sentence paragraph per area (money, love, career, health, mind) for the week, month and year
views, composed ONLY from what the reading already holds for that window: the area's helping and care lines, its own dated turns,
the window's best and quieter stretch, and the owner's per-area step. An area with no rule lines still gets a real paragraph
(steady, plus the window's best and quieter stretch); nothing is invented. Wording lives in data/area_paragraph.json."""
import json
import os
from typing import Optional

_PATH = os.path.join(os.path.dirname(__file__), "data", "area_paragraph.json")
_CACHE: dict = {}


def _data() -> dict:
    if not _CACHE:
        try:
            with open(_PATH, encoding="utf-8") as fh:
                _CACHE.update(json.load(fh))
        except Exception as e:
            print(f"[area-paragraph] data unavailable: {e}")
            _CACHE["_empty"] = True
    return _CACHE


def _dot(s: str) -> str:
    s = (s or "").strip()
    return s if not s or s.endswith((".", "!", "?")) else s + "."


def _low(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def paragraph(domain: dict, *, scope: str, relation: str, lang: str, areas_by_key: dict, area_keys: tuple,
              turns: list, best: Optional[dict], avoid: Optional[dict], steps: dict) -> Optional[str]:
    """One paragraph for one area read (`domain` is a _domain_reads row). None when the wording data is missing."""
    d = _data().get(lang) or _data().get("en")
    if not d:
        return None
    past = relation == "past"
    when = (d["when"].get(scope) or d["when"]["month"]).get(relation if relation in ("next", "past") else "current")
    tone = domain.get("tone") or "quiet"
    out = [d["lead_past" if past else "lead"][tone].format(area=domain["label"], when=when)]
    lines = [l["text"] for l in domain.get("lines") or [] if l.get("text")]
    if tone == "quiet" or not lines:
        out.append(d["quiet_body_past" if past else "quiet_body"])
    elif tone == "mixed" and len(lines) > 1:
        out += [_dot(lines[0]), d["catch_past" if past else "catch"].format(text=_low(_dot(lines[1])))]
    elif tone == "care":
        out.append(d["catch_past" if past else "catch"].format(text=_low(_dot(lines[0]))))
    else:
        out.append(_dot(lines[0]))
    mine = [a for k in area_keys for a in [areas_by_key.get(k)] if a]
    if not past and tone in ("good", "mixed"):
        step = next((steps[k] for k in area_keys if k in steps and (areas_by_key.get(k) or {}).get("lean_in")), None)
        if step:
            out.append(_dot(step))
    own_turn = next((t for t in turns or [] if t.get("area") in area_keys and t.get("text") and t.get("label")), None)
    if own_turn and len(out) < 4:
        out.append(d["turn"].format(label=own_turn["label"], text=_low(_dot(own_turn["text"]))))
    if best and best.get("label") and tone in ("good", "mixed", "quiet"):
        out.append(d["best_window_past" if past else "best_window"].format(label=best["label"]))
    elif avoid and avoid.get("label") and tone in ("care", "mixed"):
        out.append(d["avoid_window_past" if past else "avoid_window"].format(label=avoid["label"]))
    return " ".join(out)
