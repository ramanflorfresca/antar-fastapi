"""
antar_engine/wa_scrub.py — de-identify a WhatsApp message before it can enter a training set.

Pure regex, deterministic, no network. It removes what is unambiguous (emails, phone numbers, links,
long digit runs, full birth-style dates, the person's own names). It does NOT make free text
anonymous — a story can identify someone with no pattern in it — which is why training export also
requires explicit consent and never retroactive data (scripts/export_wa_training.py).
"""
from __future__ import annotations

import re
from typing import Iterable

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.I)
_PHONE = re.compile(r"(?<![\w/])\+?\d[\d\s().-]{7,}\d(?![\w/])")
_LONGNUM = re.compile(r"\b\d{9,}\b")
# a full date carrying an old year reads as a birth date: 14/03/1987, 1987-03-14, 14 March 1987
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|abr|ago|dic)[a-z]*"
_BIRTH = re.compile(
    rf"\b(?:\d{{1,2}}[/.-]\d{{1,2}}[/.-](?:19\d\d|20[01]\d)|(?:19\d\d|20[01]\d)[/.-]\d{{1,2}}[/.-]\d{{1,2}}"
    rf"|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:de\s+)?{_MONTH}\s+(?:de\s+)?(?:19\d\d|20[01]\d)"
    rf"|{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+(?:19\d\d|20[01]\d))\b", re.I)


def scrub(text: str, names: Iterable[str] = ()) -> str:
    t = text or ""
    t = _EMAIL.sub("[EMAIL]", t)
    t = _URL.sub("[LINK]", t)
    t = _BIRTH.sub("[DATE]", t)
    t = _PHONE.sub("[PHONE]", t)
    t = _LONGNUM.sub("[NUMBER]", t)
    for n in names:
        n = (n or "").strip()
        if len(n) >= 2:
            t = re.sub(rf"\b{re.escape(n)}\b", "[NAME]", t, flags=re.I)
    return t.strip()
