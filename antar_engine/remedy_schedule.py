"""
antar_engine/remedy_schedule.py
───────────────────────────────
Plain "what do I do, and when?" fields for the material remedies on the practice response.

Additive only. For each remedy dict in `today_priority` (food, gemstone, giving, fast, energy_diagram,
and the legacy daan / vrat / yantra keys) it adds:

  title            verb-led action ("Eat sweet, fragrant, dairy-rich foods on Fridays")
  frequency        "weekly" | "once"
  frequency_label  "Every Friday" | "Set up once"   (en / es / pt)
  optional         True for the supports the user can skip (gemstone, energy diagram, fast)
  weekday          ISO weekday number 1-7 (Mon=1) for weekly items, else None
  next_date        the next occurrence of that weekday on or after the user's local today (ISO), else None

and capitalises a leading lowercase letter on the prose fields (the personaliser swaps a planet name
for a lowercase energy phrase, so "Venus wants…" became "your love and partnership energy wants…").
Active items get `frequency` ("daily" | "period") from their cadence.

Pure and never raises: a failure leaves the response untouched.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from typing import Optional

_DAYS = {
    1: {"en": "Monday", "es": "lunes", "pt": "segunda-feira"},
    2: {"en": "Tuesday", "es": "martes", "pt": "terça-feira"},
    3: {"en": "Wednesday", "es": "miércoles", "pt": "quarta-feira"},
    4: {"en": "Thursday", "es": "jueves", "pt": "quinta-feira"},
    5: {"en": "Friday", "es": "viernes", "pt": "sexta-feira"},
    6: {"en": "Saturday", "es": "sábado", "pt": "sábado"},
    7: {"en": "Sunday", "es": "domingo", "pt": "domingo"},
}


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s).lower()) if unicodedata.category(c) != "Mn").strip()


_NAME_TO_NUM = {}
for _n, _names in _DAYS.items():
    for _v in _names.values():
        _NAME_TO_NUM[_fold(_v)] = _n
        _NAME_TO_NUM[_fold(_v).split("-")[0]] = _n          # "sexta" for "sexta-feira"

_LABELS = {
    "every": {"en": "Every {day}", "es": "Cada {day}", "pt": "Toda {day}"},
    "once": {"en": "Set up once", "es": "Se configura una vez", "pt": "Configura uma vez"},
}
_TITLES = {
    "food_eat": {"en": "Eat {x} on {day}s", "es": "Come {x} los {day}", "pt": "Coma {x} às {day}s"},
    "food_guide": {"en": "Follow your {day} food guide", "es": "Sigue tu guía de comida del {day}", "pt": "Siga seu guia de comida de {day}"},
    "fast": {"en": "Fast gently on {day}s", "es": "Ayuna con suavidad los {day}", "pt": "Jejue com leveza às {day}s"},
    "gem": {"en": "Wear your {name}", "es": "Usa tu {name}", "pt": "Use sua {name}"},
    "yantra": {"en": "Set up your {name}", "es": "Configura tu {name}", "pt": "Configure seu {name}"},
}
_PROSE_FIELDS = ("one_line", "why_for_this_user", "principle", "description", "best_time", "why")
_OPTIONAL = {"gemstone": True, "energy_diagram": True, "yantra": True, "fast": True, "vrat": True,
             "food": False, "giving": False, "daan": False}


def _lang(language) -> str:
    l = str(language or "en").split("-")[0].lower()
    return l if l in ("en", "es", "pt") else "en"


def _cap_first(s):
    if isinstance(s, str) and s and s[0].isalpha() and s[0].islower():
        return s[0].upper() + s[1:]
    return s


def weekday_number(name) -> Optional[int]:
    if not name:
        return None
    return _NAME_TO_NUM.get(_fold(name)) or _NAME_TO_NUM.get(_fold(name).split("-")[0])


def next_weekday_on_or_after(today: date, weekday: int) -> date:
    return today + timedelta(days=(weekday - today.isoweekday()) % 7)


def _day_name(num: int, lang: str) -> str:
    return _DAYS[num][lang]


def _title(key: str, item: dict, day_en: Optional[str], lang: str) -> Optional[str]:
    day = _day_name(weekday_number(day_en), lang) if weekday_number(day_en) else None
    if key == "food" and day:
        m = re.search(r"\bwants\s+(.+?)(?:\s+—|\.|$)", str(item.get("one_line") or ""), re.I)
        if m and lang == "en":
            return _TITLES["food_eat"]["en"].format(x=m.group(1).strip().rstrip(","), day=day)
        return _TITLES["food_guide"][lang].format(day=day)
    if key == "giving":
        first = str(item.get("one_line") or "").split(" — ")[0].strip().rstrip(".")
        return _cap_first(first) or None
    if key in ("fast", "vrat") and day:
        return _TITLES["fast"][lang].format(day=day)
    if key == "gemstone" and item.get("name"):
        return _TITLES["gem"][lang].format(name=str(item["name"]).lower())
    if key in ("energy_diagram", "yantra") and item.get("name"):
        return _TITLES["yantra"][lang].format(name=item["name"])
    return None


def annotate_practice_response(resp: dict, local_today: date, language: str = "en") -> dict:
    """Mutates and returns resp. Never raises."""
    try:
        lang = _lang(language)
        tp = (resp or {}).get("today_priority") or {}
        for key in ("food", "gemstone", "giving", "fast", "energy_diagram", "yantra", "daan", "vrat"):
            item = tp.get(key)
            if not isinstance(item, dict):
                continue
            for f in _PROSE_FIELDS:
                if f in item:
                    item[f] = _cap_first(item[f])
            day_raw = item.get("best_day") or item.get("day")
            wd = weekday_number(day_raw)
            weekly = key in ("food", "giving", "daan", "fast", "vrat") and wd is not None
            item["frequency"] = "weekly" if weekly else "once"
            item["frequency_label"] = (_LABELS["every"][lang].format(day=_day_name(wd, lang)) if weekly
                                       else _LABELS["once"][lang])
            item["optional"] = bool(_OPTIONAL.get(key, False))
            item["weekday"] = wd if weekly else None
            item["next_date"] = next_weekday_on_or_after(local_today, wd).isoformat() if weekly else None
            t = _title(key, item, _DAYS[wd]["en"] if wd else None, lang)
            if t:
                item["title"] = t
        for a in (resp or {}).get("active") or []:
            if isinstance(a, dict):
                a["frequency"] = "daily" if a.get("cadence") == "daily_tunein" else "period"
    except Exception:
        pass
    return resp
