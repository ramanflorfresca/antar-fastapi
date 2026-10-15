"""[ritual-today 2026-10-14] ONE plain-language "plan for today" payload for the Ritual screen.

It only AGGREGATES engines that already exist (practice schedule / Lal Kitab year read, daily wisdom, material
advice, vastu, the daily card's food). No new astrology. The front end renders it and never decides anything.

Contract (see Antar.world/LOVABLE_BRIEF_ritual_prescription.md):
  * every user-facing string is plain language; a string that would leak jargon is dropped, never shown
  * each card is {"status": "ready" | "hidden", ...}; a card with no real chart source is hidden, never generic copy
  * `why_chart` is internal (audit + outcome loop) and is stripped by the route before it leaves the server
  * the colour of the day is gated by material_advice.assess_color: it is never a colour that reads `avoid`
    for this chart, and never a colour the Lal Kitab year read says to refuse

Pure functions: no network, no database. The route in main.py gathers the inputs."""
from __future__ import annotations

import json
import re
from datetime import date as _date
from typing import Optional

VERSION = "ritual-today-1"

from antar_engine import ritual_why as _rw

# ── plain-language guard ─────────────────────────────────────────────────────────────────────────────────────────
_BANNED = re.compile(
    r"(?i)\b(lal\s*kitab|varshphal|varshaphal|dasha|mahadasha|antardasha|nakshatra|vata|pitta|kapha|karaka|"
    r"yogakaraka|saturn|mercury|venus|mars|jupiter|rahu|ketu|navatara|tara\s*bala|vimsottari|lagna|"
    r"\d+(?:st|nd|rd|th)\s+house|retrograde|combust|debilitat|exalt)\b")


def clean(s):
    """The string, or None when it would leak chart jargon (the caller hides that item)."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    return None if (not s or _BANNED.search(s)) else s


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


# ── colours: the backend owns every hex ──────────────────────────────────────────────────────────────────────────
_HEX = {
    "white": "#EFEDE4", "cream": "#E9DFC3", "silver": "#C3C6CB", "pearl": "#E8E2D6", "pink": "#E8A5B8",
    "sky blue": "#8CC3E8", "blue": "#3B6FB6", "dark blue": "#2F4B7C", "navy": "#1F2F55", "black": "#2C2C2A",
    "charcoal": "#45474B", "grey": "#8A8D93", "gray": "#8A8D93", "purple": "#7B5EA7", "violet": "#7B5EA7",
    "green": "#5FA36B", "emerald": "#2E8B57", "sage": "#9CB89B", "yellow": "#E0B93A", "gold": "#C9A227",
    "golden": "#C9A227", "orange": "#E08A3A", "saffron": "#E8893A", "amber": "#E0A030", "red": "#B5483A",
    "maroon": "#7A2E34", "coral": "#E0735C", "crimson": "#A8283A", "brown": "#8A6240", "earth": "#A67C52",
    "smoky": "#6B6F76", "multicolour": "#A67C52", "turquoise": "#4FB0AE", "peach": "#EDB796",
}
# colour word -> the stone family people pair it with (only used when a year read gives stones but no colours)
_STONE_COLOUR = {"emerald": "green", "diamond": "white", "white sapphire": "white", "pearl": "white",
                 "moonstone": "white", "ruby": "red", "red coral": "red", "coral": "red", "yellow sapphire": "yellow",
                 "topaz": "yellow", "blue sapphire": "blue", "amethyst": "purple"}
_WEEKDAY_PLANET = {0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter", 4: "Venus", 5: "Saturn", 6: "Sun"}
_DAYNAME = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_NAK_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"] * 3


def hex_for(name: str) -> Optional[str]:
    n = (name or "").strip().lower()
    if n in _HEX:
        return _HEX[n]
    for k in sorted(_HEX, key=len, reverse=True):
        if k in n:
            return _HEX[k]
    return None


def split_shades(s: str) -> list:
    """"White/Pink/Sky Blue" -> [{"name": "White", "hex": ...}, ...]; shades with no known hex are dropped."""
    out, seen = [], set()
    for part in re.split(r"[/,]| or ", s or ""):
        nm = part.strip()
        hx = hex_for(nm)
        if nm and hx and nm.lower() not in seen:
            seen.add(nm.lower())
            out.append({"name": _cap(nm), "hex": hx})
    return out


def _lk_refused_colours(lk_year: dict) -> set:
    """Colour words the Lal Kitab year read tells this person to refuse ("never take ... blue clothing")."""
    refused = set()
    texts = list((lk_year or {}).get("remedies") or []) + list((lk_year or {}).get("what_to_avoid") or [])
    for t in texts:
        if not isinstance(t, str) or not re.search(r"(?i)\b(never|don'?t|do not|avoid|refuse)\b", t):
            continue
        for w in sorted(_HEX, key=len, reverse=True):
            if re.search(r"(?i)\b" + re.escape(w) + r"\b\s+(clothes|clothing|cloth|garments?|dress|shirt)", t):
                refused.add(w)
    return refused


def pick_colour_of_the_day(today: Optional[_date], nak_lord: Optional[str], favor_shades: list, assess, refused: set,
                           weekday_colours: dict, weekday_planet: Optional[str] = None, sub_lord: Optional[str] = None,
                           month_lord: Optional[str] = None, year_avoid: Optional[list] = None) -> dict:
    """The safety-gated colour of the day, chosen by a hierarchy where the longer period decides what the shorter may pick.

    YEAR sets the avoid list: a colour the year says to refuse (the year's afflicted ruler, the year's remedies) is never chosen.
    DAY candidates, in order: the weekday ruler's colour, the Moon-star ruler's colour, the Moon's sub-lord colour (one signal
    each: the same planet is not counted twice). MONTH candidate: the running sub-period ruler's colour. YEAR candidate: the
    year's favourable shades. Every candidate passes assess(colour) -> 'favor'|'neutral'|'avoid'|None. A favourable colour is
    taken in tier order (day, month, year); neutral only when nothing is favourable; avoid never. The result says which tier it
    came from (`scope`), so a month or year colour is never shown as if it were today's."""
    refused = set(refused or ()) | {str(n).lower() for n in (year_avoid or [])}
    wd_planet = weekday_planet or _WEEKDAY_PLANET[today.weekday()]
    cands = []   # (name, basis, scope)
    seen_planets = set()
    for planet, tag in ((wd_planet, "weekday_ruler"), (nak_lord, "moon_star_ruler"), (sub_lord, "moon_sub_ruler")):
        if not planet or planet in seen_planets:
            continue
        seen_planets.add(planet)
        for nm in (weekday_colours.get(planet) or []):
            cands.append((nm, f"{tag}:{planet.lower()}", "day"))
    if month_lord:
        for nm in (weekday_colours.get(month_lord) or []):
            cands.append((nm, f"month_ruler:{month_lord.lower()}", "month"))
    for nm in favor_shades:
        cands.append((nm, "year_favourable", "year"))

    tiers = {"day": {"favor": None, "neutral": None}, "month": {"favor": None, "neutral": None},
             "year": {"favor": None, "neutral": None}}
    skip, seen = [], set()
    for nm, basis, scope in cands:
        key = nm.lower()
        if key in seen:
            continue
        seen.add(key)
        hx = hex_for(nm)
        if not hx:
            continue
        v = "avoid" if any(r in key or key in r for r in refused) else assess(nm)
        if v == "avoid":
            skip.append({"name": _cap(nm), "hex": hx, "basis": basis})
        elif v in ("favor", "neutral") and tiers[scope][v] is None:
            tiers[scope][v] = {"name": _cap(nm), "hex": hx, "basis": basis, "scope": scope, "verdict": v}
    # the closest period that has anything eligible decides: a day colour (even a neutral one) beats the month's,
    # and the month's beats the year's, so the 'colour of the day' is not the year's shade every day
    for scope in ("day", "month", "year"):
        t = tiers[scope]
        if t["favor"] or t["neutral"]:
            return {"colour": t["favor"] or t["neutral"], "skip": skip}
    return {"colour": None, "skip": skip}


def month_colours(month_lord: Optional[str], weekday_colours: dict, assess, refused: set, year_avoid: Optional[list]) -> list:
    """The colours of the running month: its ruler's shades that pass the year's avoid list and the chart's own check."""
    ref = set(refused or ()) | {str(n).lower() for n in (year_avoid or [])}
    out = []
    for nm in (weekday_colours.get(month_lord or "") or []):
        key = nm.lower()
        if not hex_for(nm) or any(r in key or key in r for r in ref) or assess(nm) == "avoid":
            continue
        out.append({"name": _cap(nm), "hex": hex_for(nm)})
    return out


# ── cards ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _hidden(why: str) -> dict:
    return {"status": "hidden", "why_chart": {"hidden_because": why}}


def _day_remedy_match(text: str, today: _date) -> Optional[bool]:
    """True if the remedy names today's weekday, False if it names another, None if it names none."""
    names = [d for d in _DAYNAME if re.search(r"(?i)\b" + d[:3] + r"[a-z]*\b", text)]
    if not names:
        return None
    return _DAYNAME[today.weekday()] in names


_VERDICT_LINE = {
    "strong": "This is a strong stretch. A small steady act keeps it that way.",
    "mixed": "This is a mixed stretch. A small steady act on its day keeps things balanced.",
    "weak": "This is a testing stretch. A small steady act on its day eases the pressure.",
    "challenging": "This is a testing stretch. A small steady act on its day eases the pressure.",
}


def remedy_card(today: _date, lk_year: dict, done_ids: set, chart_data: Optional[dict] = None,
                actives: Optional[list] = None) -> dict:
    rem = [r for r in ((lk_year or {}).get("remedies") or [])
           if clean(r) and not re.match(r"(?i)\s*(never|don'?t|do not|avoid|refuse)\b", r)]
    # [chant-by-affliction 2026-10-15] a chant is offered when the area it serves is under strain: on its own weekday it
    # leads; otherwise it joins the rotation of everyday remedies. The reason names the area, never the planet.
    _extra_why = {}
    for _c in _rw.chants_for_actives(actives):
        if any(re.search(_c["key"].split("_")[0], r, re.I) for r in rem):
            continue
        rem.append(_c["title"])
        _extra_why[_c["title"]] = _c
    if not rem:
        return _hidden("no lk year remedies")
    _due = [t for t, c in _extra_why.items() if today.weekday() in c["days"]]
    todays = _due or [r for r in rem if _day_remedy_match(r, today) is True]
    agnostic = [r for r in rem if _day_remedy_match(r, today) is None]
    if todays:
        pick, cadence = todays[0], f"Every {_DAYNAME[today.weekday()]}"
    elif agnostic:
        pick, cadence = agnostic[today.toordinal() % len(agnostic)], "Keep it up through the year"
    else:
        pick = rem[0]
        nxt = next((d for d in _DAYNAME if re.search(r"(?i)\b" + d[:3], pick)), "")
        cadence = f"Next on {nxt}" if nxt else "Keep it up through the year"
    pid = "remedy_" + re.sub(r"[^a-z0-9]+", "_", pick.lower())[:40].strip("_")
    from antar_engine import ritual_details as _rd
    details = _rd.remedy_details(pick, today, chart_data)
    _chant = _rw.chant_for(pick)
    if _chant and _chant.get("how_plain"):
        details = dict(details or {}, how_plain=_chant["how_plain"])   # "11 times" is wrong for a long chant
    why = (_extra_why.get(pick) or {}).get("why_plain") or _rd.remedy_why(pick) or _VERDICT_LINE.get(str((lk_year or {}).get("verdict") or "").lower(),
                                                    "A small steady act on its day keeps your year balanced.")
    return {"status": "ready", "practice_id": pid, "title": pick.rstrip("."), "details": details,
            "why_plain": why, "chant": _chant,
            "cadence_label": cadence, "accent_hex": "#5F5E5A", "done_today": pid in done_ids,
            "why_chart": {"source": "lk_varshphal_year.remedies", "verdict": (lk_year or {}).get("verdict")}}


def _focus_mantra(practice: dict) -> Optional[dict]:
    """Today's focus mantra from the daily practice (the one with the chant audio and pitch), or None."""
    m = (((practice or {}).get("today_priority") or {}).get("mantra")) or {}
    adv = m.get("advanced") or {}
    name = clean(adv.get("transliteration")) or clean(adv.get("name")) or clean(m.get("name"))
    if not name or not m.get("audio_url"):
        return None
    return {"name": _cap(name.title() if name.isupper() else name), "audio_url": m.get("audio_url"), "tone_hz": m.get("tone_hz"),
            "count": m.get("count"), "when": clean(m.get("when")), "why": clean(m.get("why")), "label": clean(m.get("label"))}


def mantra_card(wisdom: dict, done_ids: set, practice: Optional[dict] = None) -> dict:
    fm = _focus_mantra(practice)
    if fm:
        pid = "mantra_" + re.sub(r"[^a-z0-9]+", "_", fm["name"].lower())[:30].strip("_")
        return {"status": "ready", "practice_id": pid, "text_roman": fm["name"], "repeats": 11,
                "full_count": fm["count"], "purpose_plain": fm["why"] or fm["label"],
                "best_time_plain": fm["when"], "audio_url": fm["audio_url"], "tone_hz": fm["tone_hz"],
                "accent_hex": "#E0B93A", "done_today": pid in done_ids,
                "why_this": _rw.mantra_why(((practice or {}).get("today_priority") or {}).get("planet")),
                "why_chart": {"source": "daily_practice.today_priority.mantra"}}
    m = (wisdom or {}).get("mantra") or {}
    name = clean(m.get("name"))
    if not name:
        return _hidden("no mantra")
    use = clean(m.get("use")) or ""
    reps = 11
    nums = [int(x) for x in re.findall(r"\b(\d{1,3})\b", m.get("use") or "")]
    if nums and 11 in nums:
        reps = 11
    elif nums:
        reps = min(nums)
    pid = "mantra_" + re.sub(r"[^a-z0-9]+", "_", name.lower())[:30].strip("_")
    return {"status": "ready", "practice_id": pid, "text_roman": name, "repeats": reps,
            "purpose_plain": use or None, "best_time_plain": None, "accent_hex": "#E0B93A",
            "done_today": pid in done_ids, "why_this": _rw.mantra_why(None),
            "why_chart": {"source": "daily_wisdom.mantra", "season": (wisdom or {}).get("season")}}


def verse_card(wisdom: dict, done_ids: set) -> dict:
    v = (wisdom or {}).get("verse") or {}
    meaning = clean(v.get("translation"))
    ref = v.get("source") or v.get("reference")
    if not (meaning and ref and v.get("sanskrit")):
        return _hidden("no verse")
    pid = "verse_" + re.sub(r"[^a-z0-9]+", "_", str(ref).lower()).strip("_")
    return {"status": "ready", "practice_id": pid, "sanskrit": v["sanskrit"], "transliteration": v.get("transliteration"),
            "reference": ref, "meaning_plain": meaning, "why_plain": clean((wisdom or {}).get("why_now")), "why_this": _rw.verse_why(wisdom),
            "accent_hex": "#C9A227", "done_today": pid in done_ids,
            "why_chart": {"source": "daily_wisdom.verse", "season": (wisdom or {}).get("season"),
                          "season_cause": (wisdom or {}).get("season_cause")}}


def food_card(daily: dict, done_ids: set) -> dict:
    f = (daily or {}).get("food") or {}
    eat = [x for x in (f.get("eat") or []) if clean(x)][:5]
    avoid = [x for x in (f.get("avoid") or []) if clean(x)][:4]
    if not eat:
        return _hidden("no food guidance")
    tex = clean(f.get("texture"))
    head = f"Eat {tex} foods today." if tex else "What to eat today."
    from antar_engine import ritual_details as _rd
    why_this = _rw.food_why(f)
    details = _rd.food_details(f)
    if why_this and why_this.get("adds_plain") and avoid:
        details["why_avoid_plain"] = why_this["adds_plain"]   # the old line said the opposite of the Eat list
    return {"status": "ready", "practice_id": "food_today", "headline": head, "eat": eat, "avoid": avoid,
            "details": details, "why_this": why_this,
            "why_plain": clean(f.get("why_eat")) or clean(f.get("why")), "accent_hex": "#5FA36B",
            "done_today": "food_today" in done_ids,
            "why_chart": {"source": "daily.food", "planet": f.get("planet"), "mode": f.get("mode")}}


_ZONE_BEARING = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
# classical corner colours (the vastu engine ships no colours). Soft, plain; backend-owned.
_ZONE_COLOUR = {"N": ("#7FB069", "Fresh greens and blues suit this side."),
                "NE": ("#D9B84A", "Light yellow and white keep this corner open."),
                "E": ("#7FB069", "Fresh green and cream suit this side."),
                "SE": ("#E08A3A", "Warm oranges and soft pinks suit this corner."),
                "S": ("#E0735C", "Warm reds and corals suit this side."),
                "SW": ("#A67C52", "Earth brown and clay tones in this corner."),
                "W": ("#8CC3E8", "Soft blues and white suit this side."),
                "NW": ("#C3C6CB", "Grey and white suit this corner.")}
_KIND = {"sleep_head": ("sleep", "Sleep with your head toward the"), "work_facing": ("work", "Face the"),
         "eat_facing": ("eat", "Face the")}


SPACE_ABOUT = ("Vastu is the traditional way of arranging where you sleep, work and eat so your space supports your day. "
               "These directions follow your chart. Where it has no strong preference, the usual guidance is shown.")


def _space_why(why) -> Optional[str]:
    t = clean(why)
    if not t:
        return None
    t = re.sub(r"(?i)^your chart has no strong preference here, so the traditional default stands\.?$",
               "Your chart has no strong preference here, so the usual guidance applies.", t)
    if "traditional default" in t:
        return "Your chart has no strong preference here, so the usual guidance applies."
    return _cap(t)


def space_card(vastu: dict, done_ids: set) -> dict:
    if not (vastu or {}).get("available"):
        return _hidden("vastu unavailable or flag off")
    dirs, out = (vastu.get("directions") or {}), []
    for key, (kind, lead) in _KIND.items():
        d = dirs.get(key) or {}
        zone = d.get("zone")
        if zone not in _ZONE_BEARING:
            continue
        label = (d.get("label") or zone).lower()
        hx, note = _ZONE_COLOUR[zone]
        out.append({"kind": kind, "label": f"{lead} {label}" + (" while you eat" if kind == "eat" else ""),
                    "zone": zone, "bearing_deg": _ZONE_BEARING[zone], "colour_hex": hx, "colour_note_plain": note,
                    "why_plain": _space_why(d.get("why")), "status": d.get("status")})
    if not out:
        return _hidden("no directions")
    return {"status": "ready", "practice_id": "space_today", "directions": out, "accent_hex": out[0]["colour_hex"],
            "about_plain": SPACE_ABOUT,
            "done_today": "space_today" in done_ids,
            "why_chart": {"source": "vastu_engine", "src": [dirs.get(k, {}).get("src") for k in _KIND]}}


def _stone(entry: dict, caution: str) -> Optional[dict]:
    if not isinstance(entry, dict) or not clean(entry.get("stone")):
        return None
    why = clean(entry.get("why"))
    why = _cap(why) if why else why
    fing = clean(entry.get("finger"))
    return {"name": _cap(str(entry["stone"])), "why_plain": why, "finger": fing, "_metal": entry.get("metal"),
            "caution_plain": caution, "test_first": bool(entry.get("test_first"))}


def wear_card(today: _date, *, natal_mat: dict, year_mat: dict, lk_year: dict, nak_lord: Optional[str], assess,
              weekday_colours: dict, caution: str, done_ids: set, sub_lord: Optional[str] = None,
              month_lord: Optional[str] = None, daily_color: Optional[dict] = None) -> dict:
    refused = _lk_refused_colours(lk_year)
    def _ok(nm):
        k = nm.lower()
        return not any(r in k.split() or r == k or (" " in r and r in k) for r in refused) and not any(
            w in refused for w in k.split())
    fav_year = [s["name"] for e in ((year_mat or {}).get("favor") or []) for s in split_shades(e.get("shade") or e.get("color") or "")
                if _ok(s["name"])]
    fav_life = [s["name"] for e in ((natal_mat or {}).get("favorable") or natal_mat.get("favor") or [])
                for s in split_shades(e.get("shade") or e.get("color") or "") if _ok(s["name"])] if natal_mat else []
    year_avoid_names = [s_["name"] for e in ((year_mat or {}).get("avoid") or [])
                        for s_ in split_shades(e.get("shade") or e.get("color") or "")]
    pick = pick_colour_of_the_day(today, nak_lord, fav_year + fav_life, assess, refused, weekday_colours,
                                  sub_lord=sub_lord, month_lord=month_lord, year_avoid=year_avoid_names)
    col = pick["colour"]
    month_cols = month_colours(month_lord, weekday_colours, assess, refused, year_avoid_names)

    gem = ((lk_year or {}).get("gemstones") or {})
    timed = next((s for s in (_stone(e, caution) for e in (gem.get("timed") or [])) if s), None)
    life = _stone(gem.get("lifelong") or {}, caution)

    def _metal(s, fb):
        m = (s or {}).get("_metal") or fb
        return {"name": _cap(str(m)), "why_plain": None} if m else None

    life_metal = next((e.get("metal") for e in ((natal_mat or {}).get("favorable") or []) if e.get("metal")), None)
    year_colours = [{"name": n, "hex": hex_for(n)} for n in dict.fromkeys(fav_year) if hex_for(n)]
    if not year_colours and timed:
        word = _STONE_COLOUR.get(timed["name"].lower())
        if word and word not in refused:
            year_colours = [{"name": _cap(word), "hex": hex_for(word)}]
    life_colours = [s for e in ((natal_mat or {}).get("favorable") or []) for s in split_shades(e.get("shade") or e.get("color") or "")
                    if _ok(s["name"])]
    year_avoid = [s for e in ((year_mat or {}).get("avoid") or []) for s in split_shades(e.get("shade") or e.get("color") or "")]
    life_avoid = [s for e in ((natal_mat or {}).get("avoid") or []) for s in split_shades(e.get("shade") or e.get("color") or "")]
    refused_sw = [{"name": _cap(w), "hex": hex_for(w)} for w in sorted(refused) if hex_for(w)]

    scopes = {}
    if year_colours or timed:
        scopes["this_year"] = {"colors": year_colours, "avoid": year_avoid + refused_sw, "stone": timed,
                               "metal": _metal(timed, None), "note_plain": None}
    if month_cols:
        scopes["this_month"] = {"colors": month_cols, "avoid": year_avoid + refused_sw, "stone": None, "metal": None, "note_plain": None}
    if life_colours or life:
        scopes["for_life"] = {"colors": life_colours, "avoid": life_avoid, "stone": life,
                              "metal": _metal(life, life_metal), "note_plain": None}
    today_scope = None
    if col or pick["skip"]:
        from antar_engine import ritual_details as _rd
        refused_texts = [t for t in (list((lk_year or {}).get("remedies") or []) + list((lk_year or {}).get("what_to_avoid") or []))
                         if isinstance(t, str) and re.search(r"(?i)\b(never|don'?t|do not|avoid|refuse)\b", t)]
        cd = _rd.colour_details(col, daily_color or {}, pick["skip"], refused_texts)
        skip_why = {r["name"]: r["why_plain"] for r in cd.get("skip_reasons", [])}
        base = scopes.get("this_year") or scopes.get("for_life") or {}
        today_scope = {"colors": ([{"name": col["name"], "hex": col["hex"]}] if col else []),
                       "skip_today": [{"name": s["name"], "hex": s["hex"],
                                       "why_plain": skip_why.get(s["name"]) or ("Your year's remedies say to steer clear of this one."
                                                     if not _ok(s["name"]) else "Not one of your colours right now.")}
                                      for s in pick["skip"]],
                       **{k: cd[k] for k in ("where_plain", "supports_plain", "support_colour_plain") if cd.get(k)},
                       "stone": base.get("stone"), "metal": base.get("metal"),
                       "note_plain": None if col else "No colour needed today.", "colour_scope": (col or {}).get("scope")}
    if not (scopes or today_scope):
        return _hidden("no colour, stone or metal source")
    reason = None
    if col:
        wd = _DAYNAME[today.weekday()]
        ok = "it works for you" if col["verdict"] == "favor" else "it sits comfortably with your chart"
        reason = (f"{wd} suits {col['name'].lower()}, and {ok}." if col["basis"].startswith("weekday")
                  else f"{col['name']} is your colour this month, and {ok}." if col["scope"] == "month"
                  else f"{col['name']} is one of your colours this year; nothing stronger points to a colour today." if col["scope"] == "year"
                  else f"{col['name']} works for you today." if col["verdict"] == "favor"
                  else f"{col['name']} suits the Moon today, and it sits comfortably with your chart.")
    card = {"status": "ready", "practice_id": "wear_today", "default_scope": "today" if today_scope else next(iter(scopes)),
            "scope_order": [k for k in ("today", "this_month", "this_year", "for_life") if (k == "today" and today_scope) or k in scopes],
            "accent_hex": col["hex"] if col else None, "done_today": "wear_today" in done_ids,
            "why_chart": {"source": "material_advice+lk_year", "colour_basis": (col or {}).get("basis"),
                          "verdict": (col or {}).get("verdict"), "refused_by_lk": sorted(refused)}}
    if today_scope:
        card["today"] = today_scope
    card.update(scopes)
    card["_colour_of_the_day"] = ({"name": col["name"], "hex": col["hex"], "reason_plain": reason, "scope": col["scope"],
                                   "verdict": col["verdict"], "why_chart": {"basis": col["basis"]}} if col else None)
    return card


# ── the payload ──────────────────────────────────────────────────────────────────────────────────────────────────
def why_plan(headline, subline, cod, cards) -> dict:
    """The plain reasons behind today's plan, for the 'Why this plan' sheet: one short line each, no repeats, no method names."""
    lines = []
    for x in (headline, subline, (cod or {}).get("reason_plain"),
              (cards.get("remedy") or {}).get("why_plain") if (cards.get("remedy") or {}).get("status") == "ready" else None,
              (cards.get("mantra") or {}).get("purpose_plain") if (cards.get("mantra") or {}).get("status") == "ready" else None,
              (cards.get("food") or {}).get("why_plain") if (cards.get("food") or {}).get("status") == "ready" else None):
        x = clean(x)
        if x and x not in lines:
            lines.append(x)
    return {"title": "Why this plan", "lines": lines,
            "note": "Each item is chosen from your chart for today. Do the ones that fit; none of them replaces medical or professional advice."}


def card_kind(key: str, card: dict, today: _date) -> str:
    """`action` = something the person does and ticks off (it gets Mark done and counts toward the day);
    `info` = guidance to read (colour, verse, space, food): no button, no count. The mantra completes by counting to its target.
    A remedy is an action only on the day it is due."""
    if key == "mantra":
        return "action"
    if key == "remedy":
        return "info" if str(card.get("cadence_label") or "").startswith("Next on") else "action"
    return "info"


def _chart_data_of(chart: Optional[dict]) -> dict:
    cd = (chart or {}).get("chart_data")
    if isinstance(cd, str):
        try:
            cd = json.loads(cd)
        except Exception:
            cd = {}
    return cd if isinstance(cd, dict) else {}


def compose(*, today: _date, language: str, chart: dict, lk: Optional[dict], schedule: dict, wisdom: dict, daily: dict,
            vastu: dict, natal_mat: dict, year_mat: dict, nak_lord: Optional[str], completed_ids: set, streak: int,
            longest: int, assess, weekday_colours: dict, caution: str, practice: Optional[dict] = None,
            sub_lord: Optional[str] = None, month_lord: Optional[str] = None) -> dict:
    lk_year = (((schedule or {}).get("lal_kitab") or {}).get("year")) or {}
    cards = {
        "wear": wear_card(today, natal_mat=natal_mat or {}, year_mat=year_mat or {}, lk_year=lk_year, nak_lord=nak_lord,
                          assess=assess, weekday_colours=weekday_colours, caution=caution, done_ids=completed_ids,
                          sub_lord=sub_lord, month_lord=month_lord,
                          daily_color=(daily or {}).get("color")),
        "remedy": remedy_card(today, lk_year, completed_ids, _chart_data_of(chart),
                              actives=(practice or {}).get("active")),
        "mantra": mantra_card(wisdom, completed_ids, practice),
        "verse": verse_card(wisdom, completed_ids),
        "space": space_card(vastu, completed_ids),
        "food": food_card(daily, completed_ids),
    }
    cod = (cards["wear"] or {}).pop("_colour_of_the_day", None)
    for k, c in cards.items():
        c["kind"] = card_kind(k, c, today)
    ready = [k for k, c in cards.items() if c.get("status") == "ready" and c["kind"] == "action"]
    done = [k for k in ready if cards[k].get("done_today")]
    dec = (daily or {}).get("decision") or {}
    headline = (_VERDICT_LINE.get(str(lk_year.get("verdict") or "").lower()) or
                "Small steady acts keep your day balanced.")
    return {"chart_id": (chart or {}).get("id"), "date": today.isoformat(), "language": language,
            "headline": headline, "subline": clean(dec.get("prediction")),
            "why_plan": why_plan(headline, clean(dec.get("prediction")), cod, cards),
            "progress": {"done": len(done), "total": len(ready)},
            "colour_of_the_day": cod, "cards": cards,
            "streak": {"current": streak, "longest": max(longest, streak),
                       "remedy_label": (cards["remedy"].get("cadence_label") if cards["remedy"].get("status") == "ready" else None)},
            "ask_context": {"surface": "ritual", "season": (wisdom or {}).get("season")},
            "version": VERSION}


def strip_internal(o):
    """Remove every `why_chart` (and any `_`-prefixed key) before the payload leaves the server."""
    if isinstance(o, dict):
        return {k: strip_internal(v) for k, v in o.items() if k != "why_chart" and not k.startswith("_")}
    if isinstance(o, list):
        return [strip_internal(x) for x in o]
    return o


def jargon_leaks(o, path="") -> list:
    """Every user-facing string in a (stripped) payload that trips the jargon guard — empty means clean."""
    bad = []
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("hex", "practice_id", "date", "language", "version", "chart_id", "kind", "zone", "status",
                     "verdict", "default_scope", "sanskrit", "transliteration", "reference", "text_roman", "metal",
                     "audio_url", "scope_order", "colour_scope", "scope"):
                continue
            bad += jargon_leaks(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            bad += jargon_leaks(v, f"{path}[{i}]")
    elif isinstance(o, str) and _BANNED.search(o):
        bad.append(path)
    return bad
