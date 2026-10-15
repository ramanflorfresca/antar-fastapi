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

import re
from datetime import date as _date
from typing import Optional

VERSION = "ritual-today-1"

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


def pick_colour_of_the_day(today: _date, nak_lord: Optional[str], favor_shades: list, assess, refused: set,
                           weekday_colours: dict) -> dict:
    """The safety-gated colour of the day.

    Candidates, in order: the weekday ruler's colour, the Moon-star ruler's colour (one signal when it is the same
    planet), then the year's favourable shades. Every candidate passes assess(colour) -> 'favor'|'neutral'|'avoid'|None.
    avoid is never chosen and is returned in `skip`. neutral is used only when nothing is favourable. Nothing eligible
    gives colour=None (the page uses its neutral theme)."""
    wd_planet = _WEEKDAY_PLANET[today.weekday()]
    cands = []   # (name, basis)
    for nm in (weekday_colours.get(wd_planet) or []):
        cands.append((nm, f"weekday_ruler:{wd_planet.lower()}"))
    if nak_lord and nak_lord != wd_planet:      # same planet = ONE signal, not two
        for nm in (weekday_colours.get(nak_lord) or []):
            cands.append((nm, f"moon_star_ruler:{nak_lord.lower()}"))
    for nm in favor_shades:
        cands.append((nm, "year_favourable"))

    favor, neutral, skip, seen = None, None, [], set()
    for nm, basis in cands:
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
        elif v == "favor" and favor is None:
            favor = {"name": _cap(nm), "hex": hx, "basis": basis, "verdict": "favor"}
        elif v == "neutral" and neutral is None:
            neutral = {"name": _cap(nm), "hex": hx, "basis": basis, "verdict": "neutral"}
    return {"colour": favor or neutral, "skip": skip}


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


def remedy_card(today: _date, lk_year: dict, done_ids: set) -> dict:
    rem = [r for r in ((lk_year or {}).get("remedies") or [])
           if clean(r) and not re.match(r"(?i)\s*(never|don'?t|do not|avoid|refuse)\b", r)]
    if not rem:
        return _hidden("no lk year remedies")
    todays = [r for r in rem if _day_remedy_match(r, today) is True]
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
    return {"status": "ready", "practice_id": pid, "title": pick.rstrip("."),
            "why_plain": _VERDICT_LINE.get(str((lk_year or {}).get("verdict") or "").lower(),
                                           "A small steady act on its day keeps your year balanced."),
            "cadence_label": cadence, "accent_hex": "#5F5E5A", "done_today": pid in done_ids,
            "why_chart": {"source": "lk_varshphal_year.remedies", "verdict": (lk_year or {}).get("verdict")}}


def mantra_card(wisdom: dict, done_ids: set) -> dict:
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
            "done_today": pid in done_ids,
            "why_chart": {"source": "daily_wisdom.mantra", "season": (wisdom or {}).get("season")}}


def verse_card(wisdom: dict, done_ids: set) -> dict:
    v = (wisdom or {}).get("verse") or {}
    meaning = clean(v.get("translation"))
    ref = v.get("source") or v.get("reference")
    if not (meaning and ref and v.get("sanskrit")):
        return _hidden("no verse")
    pid = "verse_" + re.sub(r"[^a-z0-9]+", "_", str(ref).lower()).strip("_")
    return {"status": "ready", "practice_id": pid, "sanskrit": v["sanskrit"], "transliteration": v.get("transliteration"),
            "reference": ref, "meaning_plain": meaning, "why_plain": clean((wisdom or {}).get("why_now")),
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
    return {"status": "ready", "practice_id": "food_today", "headline": head, "eat": eat, "avoid": avoid,
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
                    "why_plain": clean(d.get("why")), "status": d.get("status")})
    if not out:
        return _hidden("no directions")
    return {"status": "ready", "practice_id": "space_today", "directions": out, "accent_hex": out[0]["colour_hex"],
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
              weekday_colours: dict, caution: str, done_ids: set) -> dict:
    refused = _lk_refused_colours(lk_year)
    def _ok(nm):
        k = nm.lower()
        return not any(r in k.split() or r == k or (" " in r and r in k) for r in refused) and not any(
            w in refused for w in k.split())
    fav_year = [s["name"] for e in ((year_mat or {}).get("favor") or []) for s in split_shades(e.get("shade") or e.get("color") or "")
                if _ok(s["name"])]
    fav_life = [s["name"] for e in ((natal_mat or {}).get("favorable") or natal_mat.get("favor") or [])
                for s in split_shades(e.get("shade") or e.get("color") or "") if _ok(s["name"])] if natal_mat else []
    pick = pick_colour_of_the_day(today, nak_lord, fav_year + fav_life, assess, refused, weekday_colours)
    col = pick["colour"]

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
    if life_colours or life:
        scopes["for_life"] = {"colors": life_colours, "avoid": life_avoid, "stone": life,
                              "metal": _metal(life, life_metal), "note_plain": None}
    today_scope = None
    if col or pick["skip"]:
        base = scopes.get("this_year") or scopes.get("for_life") or {}
        today_scope = {"colors": ([{"name": col["name"], "hex": col["hex"]}] if col else []),
                       "skip_today": [{"name": s["name"], "hex": s["hex"],
                                       "why_plain": ("Your year's remedies say to steer clear of this one."
                                                     if not _ok(s["name"]) else "Not one of your colours right now.")}
                                      for s in pick["skip"]],
                       "stone": base.get("stone"), "metal": base.get("metal"),
                       "note_plain": None if col else "No colour needed today."}
    if not (scopes or today_scope):
        return _hidden("no colour, stone or metal source")
    reason = None
    if col:
        wd = _DAYNAME[today.weekday()]
        reason = (f"{wd} suits {col['name'].lower()}, and it works for you." if col["basis"].startswith("weekday")
                  else f"{col['name']} works for you today.")
    card = {"status": "ready", "practice_id": "wear_today", "default_scope": "today" if today_scope else next(iter(scopes)),
            "accent_hex": col["hex"] if col else None, "done_today": "wear_today" in done_ids,
            "why_chart": {"source": "material_advice+lk_year", "colour_basis": (col or {}).get("basis"),
                          "verdict": (col or {}).get("verdict"), "refused_by_lk": sorted(refused)}}
    if today_scope:
        card["today"] = today_scope
    card.update(scopes)
    card["_colour_of_the_day"] = ({"name": col["name"], "hex": col["hex"], "reason_plain": reason,
                                   "verdict": col["verdict"], "why_chart": {"basis": col["basis"]}} if col else None)
    return card


# ── the payload ──────────────────────────────────────────────────────────────────────────────────────────────────
def compose(*, today: _date, language: str, chart: dict, lk: Optional[dict], schedule: dict, wisdom: dict, daily: dict,
            vastu: dict, natal_mat: dict, year_mat: dict, nak_lord: Optional[str], completed_ids: set, streak: int,
            longest: int, assess, weekday_colours: dict, caution: str) -> dict:
    lk_year = (((schedule or {}).get("lal_kitab") or {}).get("year")) or {}
    cards = {
        "wear": wear_card(today, natal_mat=natal_mat or {}, year_mat=year_mat or {}, lk_year=lk_year, nak_lord=nak_lord,
                          assess=assess, weekday_colours=weekday_colours, caution=caution, done_ids=completed_ids),
        "remedy": remedy_card(today, lk_year, completed_ids),
        "mantra": mantra_card(wisdom, completed_ids),
        "verse": verse_card(wisdom, completed_ids),
        "space": space_card(vastu, completed_ids),
        "food": food_card(daily, completed_ids),
    }
    cod = (cards["wear"] or {}).pop("_colour_of_the_day", None)
    ready = [k for k, c in cards.items() if c.get("status") == "ready"]
    done = [k for k in ready if cards[k].get("done_today")]
    dec = (daily or {}).get("decision") or {}
    headline = (_VERDICT_LINE.get(str(lk_year.get("verdict") or "").lower()) or
                "Small steady acts keep your day balanced.")
    return {"chart_id": (chart or {}).get("id"), "date": today.isoformat(), "language": language,
            "headline": headline, "subline": clean(dec.get("prediction")),
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
                     "verdict", "default_scope", "sanskrit", "transliteration", "reference", "text_roman", "metal"):
                continue
            bad += jargon_leaks(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            bad += jargon_leaks(v, f"{path}[{i}]")
    elif isinstance(o, str) and _BANNED.search(o):
        bad.append(path)
    return bad
