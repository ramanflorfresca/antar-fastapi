"""
antar_engine/birth_parse.py - "15 Oct 1990, 2:30 pm, Hyderabad" -> a birth date, time and place to CONFIRM.

The add-a-person flow made people type a date, a time (with AM/PM), a city and a country into separate fields. This reads
one free line (typed or pasted) in English, Spanish, Portuguese or Roman Hinglish and returns what it found plus exactly
what it could not decide, so the app shows a confirm card with tap-to-fix chips instead of a form. Deterministic, no LLM,
never guesses silently:
  * a day/month that could be read two ways (04/05/1990) is returned as `date_ambiguous` with both readings; the caller
    passes `date_order` ("dmy" / "mdy") once the user has chosen, and the choice is remembered client-side;
  * a clock time without am/pm (2:30) is returned as `time_ambiguous` with both candidates, never assumed;
  * "morning / afternoon / evening / night", "noon", "midnight", "not sure" give an APPROXIMATE time (flagged
    time_precision=approximate / unknown) so the reading knows the birth time is soft.
Pure; the route geocodes `city_text`.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Optional

_MONTHS = {
    1: ("january", "jan", "enero", "ene", "janeiro", "janvier", "magh"),
    2: ("february", "feb", "febrero", "fevereiro", "fev", "phalgun"),
    3: ("march", "mar", "marzo", "marco", "mar"),
    4: ("april", "apr", "abril", "abr", "avril"),
    5: ("may", "mayo", "maio", "mai"),
    6: ("june", "jun", "junio", "junho"),
    7: ("july", "jul", "julio", "julho"),
    8: ("august", "aug", "agosto", "ago"),
    9: ("september", "sept", "sep", "septiembre", "setembro", "set"),
    10: ("october", "oct", "octubre", "outubro", "out"),
    11: ("november", "nov", "noviembre", "novembro"),
    12: ("december", "dec", "diciembre", "dic", "dezembro", "dez"),
}
_MONTH_LOOKUP = {w: m for m, ws in _MONTHS.items() for w in ws}
_PART_OF_DAY = {"morning": "08:00", "manana": "08:00", "madrugada": "04:00", "dawn": "05:00", "afternoon": "14:00", "tarde": "15:00",
                "evening": "18:30", "noche": "21:00", "night": "22:00", "noite": "21:00", "subah": "08:00", "dopahar": "13:00",
                "shaam": "18:30", "raat": "22:00"}
_UNKNOWN = re.compile(r"\b(don'?t know|do not know|unknown|not sure|no idea|no se|nao sei|pata nahi|pata nahin|n/?a)\b")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _valid(y: int, m: int, d: int) -> bool:
    try:
        date(y, m, d)
        return 1900 <= y <= date.today().year
    except ValueError:
        return False


def _year(y: str) -> int:
    n = int(y)
    if len(y) == 2:
        n += 2000 if n <= date.today().year % 100 else 1900
    return n


def parse_date(text: str, date_order: Optional[str] = None) -> dict:
    """-> {value|None, span, ambiguous: [iso, iso]|None, order_assumed}; span = (start, end) in `text` to strip."""
    t = _fold(text)
    out = {"value": None, "span": None, "ambiguous": None, "order_assumed": None}
    m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", t)
    if m and _valid(int(m[1]), int(m[2]), int(m[3])):
        out.update(value=date(int(m[1]), int(m[2]), int(m[3])).isoformat(), span=m.span())
        return out
    mon = "|".join(sorted(_MONTH_LOOKUP, key=len, reverse=True))
    # 15 oct 1990 / 15th of october, 1990 / 15 de octubre de 1990
    m = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th|o|º)?\s*(?:of|de|del)?\s*({mon})\.?,?\s*(?:de|del)?\s*(\d{{4}}|\d{{2}})\b", t)
    if m and _valid(_year(m[3]), _MONTH_LOOKUP[m[2]], int(m[1])):
        out.update(value=date(_year(m[3]), _MONTH_LOOKUP[m[2]], int(m[1])).isoformat(), span=m.span())
        return out
    # oct 15, 1990 / october 15th 1990
    m = re.search(rf"\b({mon})\.?\s*(\d{{1,2}})(?:st|nd|rd|th)?,?\s*(\d{{4}})\b", t)
    if m and _valid(int(m[3]), _MONTH_LOOKUP[m[1]], int(m[2])):
        out.update(value=date(int(m[3]), _MONTH_LOOKUP[m[1]], int(m[2])).isoformat(), span=m.span())
        return out
    # 15/10/1990, 10-15-90, 04.05.1990
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4}|\d{2})\b", t)
    if m:
        a, b, y = int(m[1]), int(m[2]), _year(m[3])
        dmy, mdy = (a, b), (b, a)                      # (day, month)
        ok_dmy, ok_mdy = _valid(y, dmy[1], dmy[0]), _valid(y, mdy[1], mdy[0])
        if ok_dmy and ok_mdy and a != b:
            if date_order in ("dmy", "mdy"):
                d, mo = dmy if date_order == "dmy" else mdy
                out.update(value=date(y, mo, d).isoformat(), span=m.span(), order_assumed=date_order)
            else:
                out.update(span=m.span(), ambiguous=[date(y, dmy[1], dmy[0]).isoformat(), date(y, mdy[1], mdy[0]).isoformat()])
            return out
        if ok_dmy or ok_mdy:
            d, mo = dmy if (ok_dmy and (date_order != "mdy" or not ok_mdy)) else mdy
            out.update(value=date(y, mo, d).isoformat(), span=m.span(), order_assumed=date_order)
            return out
    return out


def parse_time(text: str) -> dict:
    """-> {value|None ('HH:MM'), precision: exact|approximate|unknown|None, ambiguous: ['HH:MM','HH:MM']|None, span}."""
    t = _fold(text)
    out = {"value": None, "precision": None, "ambiguous": None, "span": None}
    if _UNKNOWN.search(t):
        out.update(value="12:00", precision="unknown")
        return out
    m = re.search(r"\b(\d{1,2})(?:[:.h](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b", t)
    if m:
        h, mi, ap = int(m[1]), int(m[2] or 0), m[3].replace(".", "")
        if 1 <= h <= 12 and mi < 60:
            h = (h % 12) + (12 if ap == "pm" else 0)
            out.update(value=f"{h:02d}:{mi:02d}", precision="exact", span=m.span())
            return out
    m = re.search(r"\b([01]?\d|2[0-3])[:.h]([0-5]\d)\b", t)
    if m and not re.search(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b", t[max(0, m.start() - 6):m.end() + 6]):
        h, mi = int(m[1]), int(m[2])
        if h >= 13 or h == 0:
            out.update(value=f"{h:02d}:{mi:02d}", precision="exact", span=m.span())
        else:                                          # 2:30 with no am/pm: never assume
            out.update(ambiguous=[f"{h % 12:02d}:{mi:02d}", f"{(h % 12) + 12:02d}:{mi:02d}"], span=m.span())
        return out
    m = re.search(r"\b(midnight|medianoche|meia[- ]noite|noon|midday|mediodia|meio[- ]dia|dopahar)\b", t)
    if m:
        v = "00:00" if m[1].startswith(("mid", "median", "meia")) and "day" not in m[1] and "dia" not in m[1] else "12:00"
        if m[1] in ("midday", "mediodia", "dopahar") or m[1].startswith(("noon", "meio-d", "meio d")):
            v = "12:00"
        out.update(value=v, precision="exact", span=m.span())
        return out
    m = re.search(r"\b(" + "|".join(_PART_OF_DAY) + r")\b", t)
    if m:
        out.update(value=_PART_OF_DAY[m[1]], precision="approximate", span=m.span())
    return out


_FILLER = re.compile(r"\b(i was |was |born|on|at|in|near|around|about|approx\w*|time|date|of birth|dob|nacio|nacido|nasceu|nascido|el|em|en|a las|as|janam|se)\b|[,;()]", re.I)


def parse(text: str, date_order: Optional[str] = None) -> dict:
    """The whole line -> {birth_date, date_ambiguous, birth_time, time_precision, time_ambiguous, city_text, missing[]}."""
    raw = (text or "").strip()
    d = parse_date(raw, date_order)
    tm = parse_time(_strip(raw, d["span"]) if d["span"] else raw)
    rest = _strip(_strip(raw, d["span"]), None)
    rest = _strip_pattern(rest, tm)          # the time words (and 'not sure') are not part of the place
    rest = re.sub(r"\b(of the time|the time|birth ?time|time of birth|birthplace|birth place|place of birth|born|nacimiento|nascimento)\b", " ", _fold(rest))
    city = re.sub(r"\s+", " ", _FILLER.sub(" ", rest)).strip(" .-/")
    city = re.sub(r"\b(am|pm|noon|midnight|morning|afternoon|evening|night|\d{1,2}[:.h]\d{2}|\d{1,2})\b", " ", city)
    city = re.sub(r"\s+", " ", city).strip(" .-/,")
    res = {"birth_date": d["value"], "date_ambiguous": d["ambiguous"], "date_order_assumed": d["order_assumed"],
           "birth_time": tm["value"], "time_precision": tm["precision"], "time_ambiguous": tm["ambiguous"],
           "city_text": city.title() if city else None}
    missing = []
    if not (res["birth_date"] or res["date_ambiguous"]):
        missing.append("date")
    if not (res["birth_time"] or res["time_ambiguous"]):
        missing.append("time")
    if not res["city_text"]:
        missing.append("place")
    res["missing"] = missing
    return res


def _strip(text: str, span) -> str:
    if not span:
        return text
    t = _fold(text)
    return (t[:span[0]] + " " + t[span[1]:]).strip()


def _strip_pattern(text: str, tm: dict) -> str:
    t = text
    t = re.sub(r"\b\d{1,2}(?:[:.h]\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b", " ", t)
    t = re.sub(r"\b(?:[01]?\d|2[0-3])[:.h][0-5]\d\b", " ", t)
    t = re.sub(r"\b(midnight|medianoche|meia[- ]noite|noon|midday|mediodia|meio[- ]dia|dopahar)\b", " ", t)
    t = re.sub(r"\b(" + "|".join(_PART_OF_DAY) + r")\b", " ", t)
    t = _UNKNOWN.sub(" ", t)
    return t
