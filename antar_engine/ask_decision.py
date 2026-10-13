"""[ask-decision-view 2026-10-13] A structured `decision` object for /ask, built from the text the engine already wrote.

The Ask pipeline appends "It holds if ..." / "It breaks if ..." to the `read` prose and returns the one move in `next`
and the chart fact in `basis`. The new answer sheet needs those as fields (prediction / holds / breaks / move / why),
the same shape Today, Month and Year already return. This only SPLITS existing text; it writes no new words and adds
no astrology. Returns None (so the old rendering stays) unless the read really has the holds/breaks structure."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

_MARK = {
    "en": (r"It holds if", r"It breaks if"),
    "es": (r"Se sostiene si", r"Se rompe si"),
    "pt": (r"Se sustenta se", r"Se rompe se"),
}


def _lang(language) -> str:
    base = str(language or "en").lower().replace("_", "-").split("-")[0]
    return base if base in _MARK else "en"


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def build(read: Any, move: Any, basis: Any, language: Optional[str] = "en") -> Optional[Dict[str, Any]]:
    """Split `read` into {prediction, holds, breaks}; `move` = next, `why` = basis. None when not decision-shaped."""
    if not isinstance(read, str) or not read.strip():
        return None
    h_m, b_m = _MARK[_lang(language)]
    mh = re.search(r"(?<![A-Za-z])" + h_m + r"\b", read, flags=re.I)
    mb = re.search(r"(?<![A-Za-z])" + b_m + r"\b", read, flags=re.I)
    if not mh and not mb:
        return None
    first = min(m.start() for m in (mh, mb) if m)
    prediction = _clean(read[:first])
    if not prediction:
        return None

    def body(m, other):
        if not m:
            return ""
        end = other.start() if (other and other.start() > m.start()) else len(read)
        return _clean(read[m.end():end]).rstrip(".") + "."

    holds, breaks = body(mh, mb), body(mb, mh)
    out: Dict[str, Any] = {"prediction": prediction, "version": "ask-decision-1"}
    if holds and holds != ".":
        out["holds"] = holds
    if breaks and breaks != ".":
        out["breaks"] = breaks
    if isinstance(move, str) and move.strip():
        out["move"] = _clean(move)
    if isinstance(basis, str) and basis.strip():
        out["why"] = _clean(basis)
    return out
