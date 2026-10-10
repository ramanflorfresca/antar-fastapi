"""
antar_engine/connection_note.py
───────────────────────────────
Split a saved person note into a heading, a body and a one-line preview.

A saved note often looks like  "How to work with Andres\\n\\nAndres is a sharp, principled advisor…".
A list that flattened the whole string showed "How to work with Andres Andres is a sharp…" (the heading
glued to the first word of the body, and a preview that cut mid-sentence). The list now gets the parts:

  note_title    the heading line, or "" when the note has none
  note_body     the note without the heading
  note_preview  the first paragraph of the body, cut at a sentence end (or a word, with "…") — never mid-word

`note` itself is unchanged. Pure; never raises.
"""
from __future__ import annotations

import re

_TITLE_MAX = 80
_PREVIEW_MAX = 180
_PREVIEW_MIN = 60
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def split_note(note) -> dict:
    out = {"note_title": "", "note_body": "", "note_preview": ""}
    try:
        text = str(note or "").replace("\r\n", "\n").replace("\r", "\n").replace("**", "").strip()
        if not text:
            return out
        first, sep, rest = text.partition("\n")
        first_s = first.strip().strip("#").strip()
        is_title = bool(sep) and rest.strip() and 0 < len(first_s) <= _TITLE_MAX and not re.search(r"[.!?]$", first_s)
        title = first_s.rstrip(":").strip() if is_title else ""
        body = rest.strip() if is_title else text
        out["note_title"] = title
        out["note_body"] = body
        out["note_preview"] = _preview(body)
    except Exception:
        pass
    return out


def _preview(body: str) -> str:
    para = re.split(r"\n\s*\n", body.strip(), maxsplit=1)[0]
    para = re.sub(r"\s+", " ", para).strip()
    if len(para) <= _PREVIEW_MAX:
        return para
    window = para[:_PREVIEW_MAX]
    ends = [m.end() for m in _SENTENCE_END.finditer(window)]
    if ends and ends[-1] >= _PREVIEW_MIN:
        return window[:ends[-1]].strip()
    cut = window.rsplit(" ", 1)[0].rstrip(",;:—-– ")
    return cut + "…"
