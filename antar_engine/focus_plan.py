"""
The 3-6 month PLAN layers for one topic, all in plain words (no method, planet or book names):
  months_strip : one cell per month, tagged good / mixed / bad / none, from the same dated signals the answers use
  chapters     : the sub-period chapters running inside the window, with dates, a plain theme, and whether the chapter's ruler
                 touches this topic's part of the chart
  turning_points: dated moments a slow-moving influence (growth, restriction, restlessness) enters or leaves this topic's part of the chart
Deterministic; nothing here forecasts beyond what the engines already compute.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from antar_engine import meanings as M, rule_registry as rr, seasons as SE, vim_levels as vl
from antar_engine.transit_signs import transit_signs

TXT = {
    "en": {"jup_in": "Growth and luck move into your {a} area.", "jup_out": "The extra lift behind your {a} area eases.",
           "sat_in": "A slow, testing influence settles into your {a} area: expect delays; steady work pays.",
           "sat_out": "The pressure on your {a} area eases.",
           "rah_in": "A restless, unconventional pull moves into your {a} area.", "rah_out": "That restless pull on your {a} area eases."},
    "es": {"jup_in": "El crecimiento y la suerte entran en tu área de {a}.", "jup_out": "El impulso extra de tu área de {a} se suaviza.",
           "sat_in": "Una influencia lenta y exigente se instala en tu área de {a}: espera demoras; el trabajo constante rinde.",
           "sat_out": "La presión sobre tu área de {a} se alivia.",
           "rah_in": "Un impulso inquieto y poco convencional entra en tu área de {a}.", "rah_out": "Ese impulso inquieto sobre tu área de {a} se calma."},
}
TONE_OF = {"jup_in": "good", "jup_out": "mixed", "sat_in": "care", "sat_out": "good", "rah_in": "mixed", "rah_out": "good"}
KIND = {"Jupiter": "jup", "Saturn": "sat", "Rahu": "rah"}


def area_houses(subjects) -> set:
    hs = set()
    for s in subjects:
        hs |= set(rr.SUBJECTS.get(s, {}).get("houses") or ())
    return hs


def months_strip(ctx, subjects, months: int, lang: str, peaks: Optional[list] = None) -> List[dict]:
    segs = []
    for s in subjects:
        try:
            segs += rr.timeline(ctx, s, months, lang)
        except Exception:
            pass
    out = []
    for k in range(months):
        a = ctx.today + timedelta(days=30 * k)
        b = a + timedelta(days=29)
        tones = {sg["tone"] for sg in segs if sg["start"][:10] <= b.isoformat() and sg["end"][:10] >= a.isoformat()}   # any overlap with the month
        tone = "mixed" if tones >= {"good", "bad"} or "mixed" in tones else ("good" if tones == {"good"} else ("bad" if tones == {"bad"} else None))
        peak = any(pk["start"] <= b.isoformat() and pk["end"] >= a.isoformat() for pk in (peaks or []))
        out.append({"start": a.isoformat(), "end": b.isoformat(), "tone": tone, "peak": peak})   # peak = the strongest stretch touches this month
    return out


def _house_of(ctx, planet: str) -> Optional[int]:
    p = ctx.planets.get(planet)
    return None if p is None else (p.sign - ctx.lagna) % 12 + 1


def chapters(ctx, subjects, months: int, lang: str) -> List[dict]:
    rows = ctx.vim
    if not rows:
        return []
    start = datetime(ctx.today.year, ctx.today.month, ctx.today.day)
    end = start + timedelta(days=int(months * 30.4))
    hs = area_houses(subjects)
    lagna_name = SE.SIGNS[ctx.lagna]
    out = []
    for ad in [r for r in rows if r["level"] == "ad" and r["end"] > start and r["start"] < end]:
        for pd in vl.subdivide(ad["lord"], ad["start"], ad["end"]):
            if pd["end"] <= start or pd["start"] >= end:
                continue
            lord = pd["lord"]
            blk = M.planet(lord, lang) or {}
            via = lord                                     # a node rules no sign: it acts through the ruler of the sign it sits in
            if lord in ("Rahu", "Ketu"):
                via = SE.SIGN_LORD.get(SE.SIGNS[ctx.planets[lord].sign]) or ""
            ruled = set(SE.houses_ruled(via, lagna_name)) if via else set()
            sits = _house_of(ctx, lord)
            supports = bool(hs & (ruled | ({sits} if sits else set())))
            out.append({"start": max(pd["start"], start).date().isoformat(), "end": min(pd["end"], end).date().isoformat(),
                        "theme": blk.get("name"), "nature": blk.get("nature"), "supports": supports,
                        "covers": blk.get("covers"), "watch": blk.get("watch"), "helps": blk.get("helps")})
    return out


def turning_points(ctx, area_label: str, subjects, months: int, lang: str) -> List[dict]:
    hs = area_houses(subjects)
    if not hs:
        return []
    lang = "es" if lang == "es" else "en"
    prev = transit_signs(ctx.today)
    out = []
    for d in range(1, int(months * 30.4) + 1):
        day = ctx.today + timedelta(days=d)
        cur = transit_signs(day)
        for planet, kind in KIND.items():
            if cur[planet] != prev[planet]:
                new_h, old_h = (cur[planet] - ctx.lagna) % 12 + 1, (prev[planet] - ctx.lagna) % 12 + 1
                # only a real change of membership counts: moving between two houses that are both part of this topic is not an event
                key = kind + "_in" if (new_h in hs and old_h not in hs) else (kind + "_out" if (old_h in hs and new_h not in hs) else None)
                if key:
                    out.append({"date": day.isoformat(), "kind": TONE_OF[key], "key": key, "text": TXT[lang][key].format(a=area_label.lower())})
        prev = cur
    return out


TL = {"en": {"peak": "Strongest stretch", "chapter": "A {theme} chapter begins ({nature})"},
      "es": {"peak": "Tramo más fuerte", "chapter": "Empieza un capítulo de {theme} ({nature})"}}


def timeline(ctx, chapters_: list, turns: list, peaks: Optional[list], near_months: int, lang: str) -> List[dict]:
    """ONE dated list from the chapters, turning points and the strongest stretch, sorted by date, each marked near (inside the focus
    horizon) or beyond. This replaces the month-by-month strip on the detail page, which would repeat the 'This month' view."""
    lang = "es" if lang == "es" else "en"
    cut = (ctx.today + timedelta(days=int(near_months * 30.4))).isoformat()
    items = []
    for pk in peaks or []:
        items.append({"date": pk["start"], "end": pk["end"], "kind": "peak", "tone": "good", "text": TL[lang]["peak"]})
    for c in chapters_:
        if c["start"] > ctx.today.isoformat():             # the running chapter is not a future event; later ones are
            items.append({"date": c["start"], "end": c["end"], "kind": "chapter", "tone": "good" if c.get("nature") == "supportive" else "care",
                          "text": TL[lang]["chapter"].format(theme=(c.get("theme") or "").lower(), nature=(c.get("nature") or "").lower())
                                  .replace("A " + (c.get("theme") or "").lower(), ("An " if (c.get("theme") or "")[:1].lower() in "aeiou" and lang == "en" else "A ") + (c.get("theme") or "").lower(), 1)})
    for t in turns:
        items.append({"date": t["date"], "end": None, "kind": "turn", "tone": t["kind"], "text": t["text"]})
    items.sort(key=lambda i: (i["date"], i["kind"]))
    for i in items:
        i["beyond"] = i["date"] > cut
    return items
