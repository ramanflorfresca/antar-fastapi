"""[why-factors 2026-10-12] The reasons behind an Ask answer as labelled factors, in plain words.

`basis` is one plain line and `basis_facts` is one technical line. This returns the same facts as a
list the "Why this reading" sheet can lay out: your long chapter, your current shift, the area of
life, the planet that rules it and where it sits, the main support. Each planet carries what its
energy is like, whether it is supportive or testing, what to watch when it is pressured and what
helps (antar_engine/meanings.py, the owner-approved table).

Same inputs as ask_basis (chart_data, dashas): nothing is computed that the chart-facts line does
not already state, and nothing is inferred. Never raises; [] when nothing can be said truthfully.
en + es; other languages get [] (the sheet then shows basis_facts as before).
"""
from datetime import date
from typing import Any, Dict, List, Optional

from antar_engine import ask_basis as B
from antar_engine import ask_basis_es as BE
from antar_engine import decision_i18n as I18
from antar_engine import meanings as M

_MON_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_MON_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_T = {
    "en": {"chapter": "Your long chapter", "shift": "Your current shift", "area": "The area of life",
           "rules": "Who runs it", "support": "The main support", "until": "until {d}",
           "again": "The same energy again, in a shorter stretch.",
           "rules_line": "{p} rules your {area}. It sits in {where}, so this area works through {channel}.",
           "support_line": "{p} is the main support for {topic}. It sits in {where}.",
           "house_label": "{name} · {n} house", "where": "your {n} house ({name})"},
    "es": {"chapter": "Tu etapa larga", "shift": "Tu cambio actual", "area": "El área de vida",
           "rules": "Quién la dirige", "support": "El apoyo principal", "until": "hasta {d}",
           "again": "La misma energía otra vez, en un tramo más corto.",
           "rules_line": "{p} rige tu {area}. Está en {where}, así que esta área funciona a través de {channel}.",
           "support_line": "{p} es el apoyo principal de {topic}. Está en {where}.",
           "house_label": "{name} · casa {n}", "where": "tu casa {n} ({name})"},
}


def _pname(name: str, lg: str) -> str:
    """The planet's own (Vedic or Spanish) name for the label: "Rahu", "Venus"; "Sol", "Júpiter" in Spanish."""
    try:
        return I18.planet(name, "es") if lg == "es" else name
    except Exception:
        return name


def _ordinal_en(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _date(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _month(d: date, lg: str) -> str:
    return f"{_MON_ES[d.month - 1]} {d.year}" if lg == "es" else f"{_MON_EN[d.month - 1]} {d.year}"


def current_periods(dashas, today: Optional[date] = None) -> Dict[str, tuple]:
    """{"md": (planet, end_date), "ad": (planet, end_date)} for the running Vimshottari chapter and shift."""
    rows = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
    today = today or date.today()
    out: Dict[str, tuple] = {}
    for r in rows:
        lv = str(r.get("level", "")).lower()
        s, e = _date(r.get("start_date")), _date(r.get("end_date"))
        if not (s and e and s <= today < e):
            continue
        key = "md" if lv in ("mahadasha", "maha", "md", "1") else "ad" if lv in ("antardasha", "antar", "ad", "2") else None
        if key:
            out[key] = (r.get("planet_or_sign") or r.get("lord_or_sign") or "", e)
    return out


def _planet_factor(kind: str, title: str, name: str, lg: str, line: str, extra: Optional[dict] = None) -> Optional[dict]:
    p = M.planet(name, lg)
    if not p:
        return None
    f = {"kind": kind, "title": title, "label": f"{p['name']} ({_pname(name, lg)})", "vedic": name,
         "nature": p["nature"], "nature_label": p["nature_label"], "verb": p["verb"],
         "line": line or p["covers"], "watch": p["watch"], "helps": p["helps"]}
    f.update(extra or {})
    return f


def build(concern: str, chart_data: Any, dashas: Any, language: str = "en", today: Optional[date] = None) -> List[dict]:
    try:
        lg = M.lang_of(language)
        if str(language or "en").split("-")[0].lower() not in ("en", "es"):
            return []
        from antar_engine.ask_consultation import CONCERN_HOUSES, CONCERN_KARAKAS
        t = _T[lg]
        houses = CONCERN_HOUSES.get(concern)
        planets = (chart_data or {}).get("planets") or {}
        lagna = ((chart_data or {}).get("lagna") or {}).get("sign")
        out: List[dict] = []

        per = current_periods(dashas, today)
        for key, title in (("md", t["chapter"]), ("ad", t["shift"])):
            if key in per and per[key][0]:
                f = _planet_factor("chapter" if key == "md" else "shift", title, per[key][0], lg,
                                   M.planet(per[key][0], lg)["covers"] if M.planet(per[key][0], lg) else "",
                                   {"until": t["until"].format(d=_month(per[key][1], lg))})
                if f and key == "ad" and "md" in per and per["md"][0] == per["ad"][0]:
                    # the same planet twice (Rahu-Rahu): say so once instead of repeating its watch / helps
                    f.update({"line": t["again"], "watch": "", "helps": "", "same_as_chapter": True})
                if f:
                    out.append(f)

        if not houses or lagna not in B._SIGNS or not planets:
            return out
        topic = (BE._TOPIC if lg == "es" else B._TOPIC).get(concern, concern)
        channels = BE._CHANNEL if lg == "es" else B._CHANNEL
        h = B._PRIMARY.get(concern, houses[0])
        hi = M.house(h, lg)
        if hi:
            out.append({"kind": "house", "title": t["area"], "label": t["house_label"].format(name=hi["name"], n=_ordinal_en(h) if lg == "en" else h),
                        "question": hi["q"], "line": hi["covers"], "watch": hi["watch"], "helps": hi["helps"],
                        "aim_line": hi["aim_line"], "aim": hi["aim"]})
        lord = B._LORD[B._SIGNS[(B._SIGNS.index(lagna) + h - 1) % 12]]
        d9 = B.d9_planets(chart_data)
        pl = planets.get(lord) or {}

        def _where(n: int) -> str:
            wi = M.house(n, lg)
            return t["where"].format(n=_ordinal_en(n) if lg == "en" else n, name=wi["name"] if wi else "")

        def _terms(name: str, row: dict) -> List[dict]:
            notes = B._dignity(name, row.get("sign"), planets, d9) if row.get("sign") else []
            return [x for x in (M.term_for_note(n, lg) for n in notes) if x]

        if pl.get("sign") and isinstance(pl.get("house"), int) and hi:
            p = M.planet(lord, lg)
            area = f"{hi['name'].lower()}" if lg == "en" else hi["name"].lower()
            f = _planet_factor("lord", t["rules"], lord, lg,
                               t["rules_line"].format(p=f"{p['name']} ({_pname(lord, lg)})", area=area, where=_where(pl["house"]),
                                                      channel=channels.get(pl["house"], "")),
                               {"sits_in": {"number": pl["house"], "name": (M.house(pl["house"], lg) or {}).get("name", "")},
                                "terms": _terms(lord, pl)})
            if f:
                out.append(f)
        for k in (CONCERN_KARAKAS.get(concern) or [])[:1]:
            if k == lord:
                continue
            kp = planets.get(k) or {}
            if kp.get("sign") and isinstance(kp.get("house"), int):
                p = M.planet(k, lg)
                if not p:
                    continue
                f = _planet_factor("support", t["support"], k, lg,
                                   t["support_line"].format(p=f"{p['name']} ({_pname(k, lg)})", topic=topic, where=_where(kp["house"])),
                                   {"sits_in": {"number": kp["house"], "name": (M.house(kp["house"], lg) or {}).get("name", "")},
                                    "terms": _terms(k, kp)})
                if f:
                    out.append(f)
        return out
    except Exception:
        return []
