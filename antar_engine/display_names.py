"""First names for display.

Connection texts (summaries, layer lines, the card) are generated and stored with whatever name was on file, so one screen could say "Raman and saransh" and the next
"Raman Singh and Andres Botero". This is applied when a payload is SERVED: every full name that has a distinct first name becomes the first name, everywhere in the payload.
Nothing stored changes. Two people who share a first name keep their full names (otherwise the text would be ambiguous).
"""
import re
from typing import Any, Iterable, List


def first(name: Any) -> str:
    return str(name or "").strip().split(" ")[0] if str(name or "").strip() else ""


def _pairs(names: Iterable[Any]) -> List[tuple]:
    names = [str(n).strip() for n in names if n and str(n).strip()]
    firsts = [first(n) for n in names]
    out = []
    for n, f in zip(names, firsts):
        if " " in n and f and firsts.count(f) == 1:
            out.append((n, f))
    out.sort(key=lambda p: -len(p[0]))
    return out


def apply(obj: Any, names: Iterable[Any]) -> Any:
    """Return `obj` with each full name replaced by its first name in every string (dicts/lists walked). Never raises."""
    try:
        pairs = _pairs(names)
        if not pairs:
            return obj
        rx = [(re.compile(r"(?<!\w)" + re.escape(full) + r"(?!\w)"), f) for full, f in pairs]

        def walk(v):
            if isinstance(v, str):
                for r, f in rx:
                    v = r.sub(f, v)
                return v
            if isinstance(v, dict):
                return {k: walk(x) for k, x in v.items()}
            if isinstance(v, list):
                return [walk(x) for x in v]
            return v
        return walk(obj)
    except Exception:
        return obj
