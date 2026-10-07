"""
antar_engine/reveal_lines.py
────────────────────────────
The two plain-words lines shown while the first chart loads:

  1. the big chapter  — the running Vimsottari mahadasha, real start/end dates
  2. the stretch in it — the running Jaimini chapter, described by life area

Rules (brief section 5): 0–2 lines; a line whose data is missing is SKIPPED,
never replaced with filler; line 2 is skipped when the birth time is unknown;
no system names in the strings; a chapter that has already ended is never shown.

PLANET NAMES: off by default (env REVEAL_LINES_PLANET_NAMES). The identity payload
has a standing rule against planet names in user-reachable text
(chart_identity.py [jargon-fix 2026-09-30]), so line 1 uses the same plain energy
phrase ("a discipline-and-time chapter"). Set REVEAL_LINES_PLANET_NAMES=1 to keep
the planet name ("a Saturn chapter", the brief's own example).
"""
from __future__ import annotations

import logging
import os
from datetime import date
from typing import List, Optional

from antar_engine import topic_copy as C
from antar_engine.house_activation import _lagna_index

logger = logging.getLogger(__name__)


def planet_names_enabled() -> bool:
    return os.getenv("REVEAL_LINES_PLANET_NAMES", "").strip().lower() in ("1", "true", "yes", "on")


def _chapter_word(planet: str, lang: str) -> Optional[str]:
    """What fills "a ___ chapter": the planet name (switch on) or the identity
    payload's plain energy phrase (default). None when there is nothing honest to say."""
    if planet_names_enabled():
        return C.pick(C.PLANET, lang).get(planet)
    from antar_engine.chart_identity import _plain_l
    plain = _plain_l("es" if lang == "es" else "pt" if lang == "pt" else "en", planet)
    if not plain:
        return None
    # en/hinglish put the phrase before a noun: "a discipline-and-time chapter"
    return plain.replace(" ", "-") if lang in ("en", "hinglish") else plain


def _d(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _running(rows, today: date, levels) -> Optional[dict]:
    best = None
    for r in rows or []:
        if str(r.get("level") or "").lower() not in levels:
            continue
        s, e = _d(r.get("start_date") or r.get("start")), _d(r.get("end_date") or r.get("end"))
        if s and e and s <= today <= e:
            if best is None or (e - s) < (best[2] - best[1]):
                best = (r, s, e)
    return best


def reveal_lines(chart_data: dict, dashas: dict, birth_date: str, birth_time_accuracy: Optional[str],
                 today: date, language: str = "en") -> List[str]:
    lang = C.serve_language(language)
    lines: List[str] = []
    try:
        big = _running((dashas or {}).get("vimsottari"), today, ("mahadasha", "maha_dasha", "1"))
        if big:
            row, s, e = big
            planet = _chapter_word(str(row.get("lord_or_sign") or row.get("planet_or_sign") or "").title(), lang)
            if planet and e >= today:
                b = _d(birth_date)
                # the first chapter starts at birth with only its remaining balance — "since birth" would lie
                from_birth = bool(b and abs((s - b).days) <= 1)
                if from_birth:
                    lines.append(C.pick(C.REVEAL_BIG_FROM_BIRTH, lang).format(
                        planet=planet, end=C.month_year(e, lang)))
                else:
                    lines.append(C.pick(C.REVEAL_BIG, lang).format(
                        planet=planet, start=C.month_year(s, lang), end=C.month_year(e, lang)))
    except Exception:
        logger.exception("[reveal] line 1 skipped")

    try:
        if (birth_time_accuracy or "").lower() != "unknown":
            from antar_engine.chara_dasha import _sign_idx
            rows = (dashas or {}).get("jaimini") or (dashas or {}).get("chara")
            cur = _running(rows, today, ("mahadasha", "maha_dasha", "1")) or \
                _running(rows, today, ("antardasha", "antar_dasha", "2"))
            if cur:
                row, s, e = cur
                si = _sign_idx(row.get("lord_or_sign") or row.get("planet_or_sign") or row.get("sign"))
                if si is not None and e >= today:
                    house = ((si - _lagna_index(chart_data)) % 12) + 1
                    area = C.pick(C.REVEAL_AREA, lang)[house]
                    lines.append(C.pick(C.REVEAL_STRETCH, lang).format(
                        area=area, start=C.month_year(s, lang), end=C.month_year(e, lang)))
    except Exception:
        logger.exception("[reveal] line 2 skipped")
    return lines[:2]
