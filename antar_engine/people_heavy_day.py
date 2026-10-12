"""[people-heavy-day 2026-10-12] "Heads-up" when a person you starred has a tender day.

A user stars up to MAX_STARS connections. In the user's local morning an hourly job reads each starred person's day
glance (the same warm-cache band the People tab shows: steady / light / friction). If a starred person's band is
`friction`, ONE push goes out for that chart that day (the first such person), never more, and never when the user has
turned the setting off. It never counts toward the daily-loop streak and is about the user's own decision ("ask today
or wait"), never about the other person's feelings.

v1 reads TODAY's glance for the person (the cache the People tab already uses). A "tomorrow" alert needs the
connection's next-day card computed ahead; that is a follow-up, so the copy says "today".
Pure helpers here; the job and endpoints live in main.py."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

MAX_STARS = 3
WINDOW_FIRST_HOUR = 8        # local hours the job may send in (8-10): the glance may still be cold at 8
WINDOW_LAST_HOUR = 10
PREF_KEY = "people_heavy_day"
ROUTE = "/circle"

_MSG = {
    "en": ("Antar", "{name} has a tender day today. If you need something from them, ask tomorrow, or go gently."),
    "es": ("Antar", "{name} tiene un día sensible hoy. Si necesitas algo de esa persona, pídelo mañana o ve con calma."),
    "pt": ("Antar", "{name} tem um dia sensível hoje. Se precisar de algo dessa pessoa, peça amanhã ou vá com calma."),
}


def norm_lang(*candidates) -> str:
    for c in candidates:
        c = str(c or "").split("-")[0].lower()
        if c in _MSG:
            return c
    return "en"


def build_message(name: str, lang: str = "en") -> tuple:
    title, body = _MSG[norm_lang(lang)]
    return title, body.format(name=(name or "").strip() or {"en": "Someone you starred", "es": "Alguien que marcaste", "pt": "Alguém que você marcou"}[norm_lang(lang)])


def in_window(now_utc: datetime, tz_hours: float) -> bool:
    h = (now_utc + timedelta(hours=float(tz_hours or 0.0))).hour
    return WINDOW_FIRST_HOUR <= h <= WINDOW_LAST_HOUR


def pref_on(notifications) -> bool:
    """The user's setting; ON when never set (the default)."""
    prefs = (notifications or {}).get("preferences") if isinstance(notifications, dict) else None
    if not isinstance(prefs, dict) or PREF_KEY not in prefs:
        return True
    return bool(prefs.get(PREF_KEY))


def pick(candidates: List[dict]) -> Optional[dict]:
    """The one person to alert for: the first starred person (oldest star) whose band is friction."""
    for c in sorted(candidates or [], key=lambda x: str(x.get("starred_at") or "")):
        if c.get("band") == "friction":
            return c
    return None


def can_star(current_stars: int, already: bool) -> bool:
    return already or int(current_stars or 0) < MAX_STARS
