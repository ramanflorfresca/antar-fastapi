"""[phase-view 2026-10-12] "Current phase": the running long chapter (Vimshottari main period) and shift (sub-period)
in plain words, with dates, progress, how the two combine, the four life areas, what comes next inside the chapter
and the turning points. Deterministic; everything is read from the dasha rows, the owner-approved meanings table
(antar_engine/meanings.py) and the Windows feed. Nothing is invented and no system names reach the reader beyond the
planet's own name. en + es; other languages get English. Never raises: [] / None parts when a fact is missing."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from antar_engine import meanings as M
from antar_engine import why_factors as WF

AREAS = (("career", "Work", "Trabajo"), ("money", "Money", "Dinero"), ("love", "Love", "Amor"), ("health", "Health", "Salud"))

_T = {
    "en": {"same": "The same energy again, in a shorter stretch. {p} runs the chapter and this shift, so its themes are strongest and its cautions too.",
           "both_good": "A supportive chapter with a supportive shift. This is a stretch to move on things, if you stay selective: {a} gives the direction and {b} gives the openings.",
           "good_test": "A supportive chapter with a testing shift. The direction is good, the pace is demanding: {a} pushes forward while {b} asks for care and patience.",
           "test_good": "A demanding chapter with a supportive shift. The shift gives you room to breathe and build inside a chapter that asks a lot.",
           "both_test": "A demanding chapter and a demanding shift. Keep commitments small and steady: {a} and {b} both ask for patience before they reward effort.",
           "mixed": "{a} sets the long direction and {b} colours this stretch. Read them together: what {a} asks for, {b} shapes in the near term.",
           "supporting": "supporting", "testing": "testing", "neutral": "steady",
           "area_open": "A good stretch is open now.", "area_care": "Go gently here for now.", "area_none": "Nothing sharp pulling here.",
           "shift_change": "The shift changes: {a} to {b}", "chapter_end": "The chapter ends",
           "next_chapter": "A new chapter begins ({p})"},
    "es": {"same": "La misma energía otra vez, en un tramo más corto. {p} dirige la etapa y este cambio, así que sus temas son más fuertes y sus cuidados también.",
           "both_good": "Una etapa de apoyo con un cambio de apoyo. Es un tramo para avanzar, si eres selectivo: {a} da la dirección y {b} las oportunidades.",
           "good_test": "Una etapa de apoyo con un cambio exigente. La dirección es buena, el ritmo pide cuidado: {a} empuja y {b} pide paciencia.",
           "test_good": "Una etapa exigente con un cambio de apoyo. El cambio te da espacio para respirar y construir dentro de una etapa que pide mucho.",
           "both_test": "Una etapa exigente y un cambio exigente. Mantén los compromisos pequeños y constantes: {a} y {b} piden paciencia antes de premiar el esfuerzo.",
           "mixed": "{a} marca la dirección larga y {b} da color a este tramo. Léelos juntos.",
           "supporting": "a favor", "testing": "exigente", "neutral": "estable",
           "area_open": "Hay un buen tramo abierto ahora.", "area_care": "Ve con cuidado aquí por ahora.", "area_none": "Nada fuerte tira aquí.",
           "shift_change": "Cambia el tramo: {a} a {b}", "chapter_end": "Termina la etapa",
           "next_chapter": "Empieza una nueva etapa ({p})"},
}


def _d(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _months_between(a: date, b: date) -> int:
    return max(0, (b.year - a.year) * 12 + (b.month - a.month))


def _nm(b: dict, lg: str) -> str:
    """"Growth (Jupiter)": the plain name with the planet's own name, the same label the Why sheet uses."""
    return f"{b['plain_name']} ({WF._pname(b['planet'], lg)})"


def _pct(s: date, e: date, today: date) -> int:
    total = (e - s).days
    if total <= 0:
        return 0
    return max(0, min(100, round(100 * (today - s).days / total)))


def _vim_rows(dashas) -> List[dict]:
    return (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []


def _lvl(r: dict) -> Optional[str]:
    lv = str(r.get("level", "")).lower()
    return "md" if lv in ("mahadasha", "maha", "md", "1") else "ad" if lv in ("antardasha", "antar", "ad", "2") else None


def _planet_block(name: str, lg: str, s: date, e: date, today: date) -> Optional[dict]:
    p = M.planet(name, lg)
    if not p:
        return None
    return {"planet": name, "plain_name": p["name"], "start": s.isoformat(), "end": e.isoformat(),
            "progress_pct": _pct(s, e, today), "months_left": _months_between(today, e),
            "nature": p["nature"], "nature_label": p["nature_label"], "verb": p["verb"],
            "line": p["covers"], "watch": p["watch"], "helps": p["helps"]}


def combine(md: Optional[dict], ad: Optional[dict], lg: str) -> str:
    """One plain paragraph on how the chapter and the shift work together."""
    if not md or not ad:
        return ""
    t = _T[lg]
    if md["planet"] == ad["planet"]:
        return t["same"].format(p=_nm(md, lg))
    a, b = _nm(md, lg), _nm(ad, lg)
    na, nb = md["nature"], ad["nature"]
    if na == "supportive" and nb == "supportive":
        k = "both_good"
    elif na == "supportive" and nb == "testing":
        k = "good_test"
    elif na == "testing" and nb == "supportive":
        k = "test_good"
    elif na == "testing" and nb == "testing":
        k = "both_test"
    else:
        k = "mixed"
    return t[k].format(a=a, b=b)


def life_areas(feed: Optional[dict], lg: str) -> List[dict]:
    """Work / Money / Love / Health from the Windows feed (open window = supporting, careful = testing)."""
    t = _T[lg]
    now = {w.get("topic"): w.get("kind") for w in ((feed or {}).get("now") or [])}
    out = []
    for key, en, es in AREAS:
        kind = now.get(key)
        state = "supporting" if kind == "open" else "testing" if kind == "care" else "neutral"
        line = t["area_open"] if kind == "open" else t["area_care"] if kind == "care" else t["area_none"]
        out.append({"area": es if lg == "es" else en, "topic": key, "state": state,
                    "state_label": t[state], "line": line})
    return out


def build(dashas: Any, feed: Optional[dict] = None, language: str = "en", today: Optional[date] = None) -> dict:
    try:
        lg = M.lang_of(language)
        today = today or date.today()
        rows = _vim_rows(dashas)
        per = WF.current_periods(dashas, today)
        if "md" not in per:
            return {"available": False}
        md_planet, md_end = per["md"]
        md_start = next((_d(r.get("start_date")) for r in rows
                         if _lvl(r) == "md" and (r.get("planet_or_sign") or r.get("lord_or_sign")) == md_planet
                         and _d(r.get("end_date")) == md_end and _d(r.get("start_date")) and _d(r.get("start_date")) <= today), None)
        chapter = _planet_block(md_planet, lg, md_start or today, md_end, today) if md_start else None
        shift = None
        if "ad" in per:
            ad_planet, ad_end = per["ad"]
            ad_start = next((_d(r.get("start_date")) for r in rows
                             if _lvl(r) == "ad" and (r.get("planet_or_sign") or r.get("lord_or_sign")) == ad_planet
                             and _d(r.get("end_date")) == ad_end and _d(r.get("start_date")) and _d(r.get("start_date")) <= today), None)
            if ad_start:
                shift = _planet_block(ad_planet, lg, ad_start, ad_end, today)
                if shift and ad_planet == md_planet:
                    shift["same_as_chapter"] = True
        # upcoming shifts inside the chapter, soonest first
        upcoming = []
        for r in sorted((r for r in rows if _lvl(r) == "ad"), key=lambda r: str(r.get("start_date"))):
            s, e = _d(r.get("start_date")), _d(r.get("end_date"))
            nm = r.get("planet_or_sign") or r.get("lord_or_sign") or ""
            if not (s and e) or s <= today or s >= md_end or str(r.get("parent_lord") or md_planet) != md_planet:
                continue
            b = _planet_block(nm, lg, s, e, today)
            if b:
                upcoming.append(b)
        t = _T[lg]
        turning = []
        if shift and upcoming:
            nxt = upcoming[0]
            turning.append({"date": nxt["start"], "label": t["shift_change"].format(a=_nm(shift, lg), b=_nm(nxt, lg)),
                            "in_months": _months_between(today, _d(nxt["start"]))})
        nxt_md = next((r for r in sorted((r for r in rows if _lvl(r) == "md"), key=lambda r: str(r.get("start_date")))
                       if _d(r.get("start_date")) and _d(r.get("start_date")) >= md_end), None)
        nm_next = M.planet((nxt_md or {}).get("planet_or_sign") or (nxt_md or {}).get("lord_or_sign") or "", lg)
        turning.append({"date": md_end.isoformat(),
                        "label": t["next_chapter"].format(p=nm_next["name"]) if nm_next else t["chapter_end"],
                        "in_months": _months_between(today, md_end)})
        return {"available": True, "chapter": chapter, "shift": shift,
                "how_they_combine": combine(chapter, shift, lg),
                "life_areas": life_areas(feed, lg),
                "upcoming_shifts": upcoming[:4], "turning_points": turning, "language": lg}
    except Exception as e:
        print(f"[phase-view] build skipped: {e!r}")
        return {"available": False}
