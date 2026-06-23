"""
lk_varshphal_year.py — deterministic Lal Kitab reading engine (year + month).

PREVIEW / flagged. Reads rule data from `lk_year_rules` + the authentic annual
progression table; degrades gracefully where data is missing.

Placements:
  YEAR  (Varshphal): annual house = VARSHAPHAL_TABLE[running_year][natal_house]
  MONTH (Masik):     annual house advanced one house per month since birthday

Reading layers (shared): single planet × house verdict × dusthana/8th-event ×
bait/transfer × friend-foe (spoil/strengthen) × two-planet combos × transit.

USER-FACING OUTPUT (plain=True, the default): translated to plain life-nouns —
NO planet names, NO house numbers (project rule 12). A final guardrail strips
any that slip through. plain=False keeps the technical wording for admin/debug.
"""
import re
from datetime import date

from antar_engine import lk_year_rules as R
from antar_engine.varshaphal_table import get_annual_house

try:
    from antar_engine.chart_context_builder import HOUSE_KARAKAS
except Exception:  # pragma: no cover
    HOUSE_KARAKAS = {}

try:
    from antar_engine.lal_kitab import REMEDIES as _LK_REMEDIES
except Exception:  # pragma: no cover
    _LK_REMEDIES = {}

_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
          "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_PRIORITY = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
_SLOW = ("Saturn", "Jupiter", "Rahu", "Ketu")
_MALEFIC_TRANSIT = ("Saturn", "Rahu", "Ketu")

# ── guardrail: never let a planet name or house number reach the user ──
_PLANET_RX = re.compile(r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b")


def _no_jargon(s):
    """Strip planet names + house numbers from a user-facing string."""
    if not isinstance(s, str):
        return s
    # drop any parenthetical that names a planet
    s = re.sub(r"\s*\([^)]*\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b[^)]*\)", "", s)
    s = _PLANET_RX.sub("a planetary influence", s)
    s = re.sub(r"\bhouse\s*\d+\b", "this area", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    return s.strip()


def _age(birth_date, today=None):
    try:
        b = date.fromisoformat(str(birth_date)[:10])
    except Exception:
        return None
    t = today or date.today()
    return max(0, t.year - b.year - ((t.month, t.day) < (b.month, b.day)))


def _house_domain(h):
    return (HOUSE_KARAKAS.get(h, "") or "").split(",")[0].strip() or "this area"


def _remedy_text(planet, house):
    pr = _LK_REMEDIES.get(planet) or {}
    obj = pr.get(house) or pr.get("general")
    if obj is None:
        return None
    return getattr(obj, "instructions", None) or (obj.get("instructions") if isinstance(obj, dict) else None)


def _book_remedy(planet, verdict, house):
    if verdict and verdict.get("refs") and R.LK_REMEDY_LIST.get(planet):
        for ref in verdict["refs"]:
            t = R.LK_REMEDY_LIST[planet].get(ref)
            if t:
                return t
    return _remedy_text(planet, house)


def _natal_houses(natal_chart):
    out = {}
    planets = (natal_chart or {}).get("planets") or (natal_chart or {}).get("planet_positions") or {}
    if isinstance(planets, dict):
        for p, v in planets.items():
            if isinstance(v, dict) and isinstance(v.get("house"), int):
                out[p] = v["house"]
    elif isinstance(planets, list):
        for v in planets:
            if isinstance(v, dict):
                nm = v.get("name") or v.get("planet")
                if nm and isinstance(v.get("house"), int):
                    out[nm] = v["house"]
    return out


def _lagna_index(natal_chart):
    lg = (natal_chart or {}).get("lagna") or (natal_chart or {}).get("ascendant")
    sign = lg.get("sign") or lg.get("rashi") if isinstance(lg, dict) else (lg if isinstance(lg, str) else None)
    if sign:
        try:
            return _SIGNS.index(str(sign).strip().title())
        except ValueError:
            return None
    return None


def transit_houses_now(lagna_idx, today=None):
    """Current slow-planet houses from the natal lagna (whole-sign). Graceful."""
    if lagna_idx is None:
        return {}
    try:
        from antar_engine.transit_engine import get_current_transit_positions
        from datetime import datetime as _dt
        pos = get_current_transit_positions(_dt.combine(today, _dt.min.time()) if today else None)
        out = {}
        for p in _SLOW:
            d = pos.get(p)
            if d and isinstance(d.get("sign_index"), int):
                out[p] = ((d["sign_index"] - lagna_idx) % 12) + 1
        return out
    except Exception:
        return {}


def _domain_label(p, ah, gender, plain):
    spouse = R.spouse_karaka(gender)
    if plain:
        if p == spouse:
            return "your husband" if spouse == "Jupiter" else "your wife"
        return R.PLAIN_DOMAIN.get(p) or _house_domain(ah)
    sig = R.planet_significations(p, gender)
    return sig[0] if sig else _house_domain(ah)


def _bait_suffers(p, plain):
    bait = R.LK_BAIT_TRANSFER.get(p)
    if not bait or not bait.get("suffers"):
        return None
    s = bait["suffers"]
    if plain:
        s = re.sub(r"\s*\(via [^)]+\)", "", s)
        s = s.replace("its friend-planets' domains", "the people close to you")
        s = s.replace("the native's", "your")
    return s


def _read_placements(placements, gender, transit_houses, age, period="year", plain=True):
    spouse = R.spouse_karaka(gender)
    period_w = "this year" if period == "year" else "this month"

    occupants = {}
    for p, h in placements.items():
        occupants.setdefault(h, []).append(p)

    combinations = []
    for h, plist in occupants.items():
        if len(plist) < 2:
            continue
        for a, b, eff, plain_eff in R.LK_COMBINATIONS:
            if a in plist and b in plist:
                if "4th house" in eff and h != 4:
                    continue
                txt = plain_eff if plain else eff
                area = _house_domain(h) if plain else _house_domain(h)
                combinations.append(f"In {area}, {txt}.")

    happen, avoid, remedies, events, notes = [], [], [], [], []
    strained_planets = []
    n_support = n_strain = 0

    for p in _PRIORITY:
        ah = placements.get(p)
        if not ah:
            continue
        domain = _domain_label(p, ah, gender, plain)
        verdict = (R.LK_HOUSE_VERDICTS.get(p, {}) or {}).get(ah) or {}

        co = [x for x in occupants.get(ah, []) if x != p]
        ff = R.LK_FRIEND_FOE.get(p, {})
        foes_here = [x for x in co if x in ff.get("foes", [])]
        friends_here = [x for x in co if x in ff.get("friends", [])]

        base_strained = ah in R.DUSTHANA
        base_supported = ah in (R.KENDRA + R.TRIKONA) or (p == "Saturn" and ah in R.SATURN_BENEFIC_HOUSES)
        spoiled = bool(foes_here) and not friends_here
        eased = bool(friends_here) and not foes_here
        strained = base_strained or (spoiled and not base_supported)
        supported = (base_supported or eased) and not strained

        t_here = [sp for sp in _SLOW if transit_houses.get(sp) == ah]
        t_malefic = [sp for sp in t_here if sp in _MALEFIC_TRANSIT]
        t_event = [sp for sp in _MALEFIC_TRANSIT if transit_houses.get(sp) == R.EVENT_HOUSE]

        def _foe_note():
            if not foes_here:
                return ""
            return " (a competing influence here works against it.)" if plain else f" ({', '.join(foes_here)} shares this area and spoils it.)"

        def _friend_note():
            if not friends_here:
                return ""
            return " (a supporting influence here strengthens it.)" if plain else f" ({', '.join(friends_here)} shares this area and strengthens it.)"

        def _transit_note(easing=False):
            if easing:
                return (" A supportive cycle eases this area " + period_w + ".") if plain else f" Transiting Jupiter eases this area {period_w}."
            return (" The current slow cycle sharpens it " + period_w + ".") if plain else f" Transiting {', '.join(t_malefic)} sharpens it {period_w}."

        if strained:
            n_strain += 1
            strained_planets.append(p)
            what = verdict.get("bad") or f"pressure on {domain}"
            line = f"{domain.capitalize()}: {what}."
            suff = _bait_suffers(p, plain)
            if suff:
                line += f" The strain can surface through {suff}."
            line += _foe_note()
            if t_malefic:
                line += _transit_note()
            happen.append(line)
            avoid.append(f"Don't force big moves in {domain} {period_w}.")
            rt = _book_remedy(p, verdict, ah)
            if rt:
                remedies.append({"text": rt} if plain else {"planet": p, "house": ah, "text": rt})
            if ah == R.EVENT_HOUSE or t_malefic or (p in t_event):
                if p == spouse:
                    tag = "your husband and marriage" if spouse == "Jupiter" else "your wife and marriage"
                else:
                    tag = domain
                events.append(f"A sudden, unexpected turn around {tag} (loss or unexpected gain) is possible {period_w}.")
        elif supported:
            n_support += 1
            what = verdict.get("good") or f"strength in {domain}"
            line = f"{domain.capitalize()}: {what}."
            line += _friend_note()
            if "Jupiter" in t_here:
                line += _transit_note(easing=True)
            happen.append(line)

        if base_supported and foes_here:
            base = f"{domain.capitalize()} is well placed but " + ("a competing influence" if plain else ', '.join(foes_here)) + " can spoil it — handle with care."
            notes.append(base)

    overall = "supportive" if (n_support and not n_strain) else ("challenging" if (n_strain and not n_support) else "mixed")

    if plain:
        happen = [_no_jargon(x) for x in happen]
        avoid = [_no_jargon(x) for x in avoid]
        events = [_no_jargon(x) for x in events]
        combinations = [_no_jargon(x) for x in combinations]
        notes = [_no_jargon(x) for x in notes]
        remedies = [{"text": _no_jargon(r["text"])} for r in remedies]

    return {
        "available": True, "period": period, "verdict": overall,
        "what_will_happen": happen[:7], "what_to_avoid": avoid[:5],
        "remedies": remedies[:5], "life_events": events[:4],
        "combinations": combinations[:4], "notes": notes[:3],
        "_debug": {
            "age": age, "gender": gender, "spouse_karaka": spouse, "plain": plain,
            "placements": placements,
            "shared_houses": {h: ps for h, ps in occupants.items() if len(ps) >= 2},
            "transit_houses": transit_houses,
            "strained_planets": strained_planets,
        },
    }


def _gemstones(natal_chart, strained_planets, age, period):
    """Lifelong (Parashari) + timed (LK) stone suggestions. Never raises."""
    try:
        from antar_engine import lk_gemstone as _gem
        pl = (natal_chart or {}).get("planets") or (natal_chart or {}).get("planet_positions") or {}
        lg = (natal_chart or {}).get("lagna") or (natal_chart or {}).get("ascendant")
        return _gem.build(pl, lg, strained_planets, age, period=period)
    except Exception:
        return {"lifelong": None, "timed": []}


def _prep(natal_chart, birth_date, transit_houses, today, use_transit):
    age = _age(birth_date, today)
    natal = _natal_houses(natal_chart)
    if age is None or not natal:
        return None, None, None
    if transit_houses is None and use_transit:
        transit_houses = transit_houses_now(_lagna_index(natal_chart), today=today)
    return age, natal, (transit_houses or {})


def read_year(natal_chart, birth_date, gender="", transit_houses=None, today=None, use_transit=True, plain=True):
    """LK Varshphal YEAR reading. Never raises."""
    try:
        age, natal, th = _prep(natal_chart, birth_date, transit_houses, today, use_transit)
        if age is None:
            return {"available": False, "reason": "missing age or natal houses"}
        placements = {p: get_annual_house(nh, age) for p, nh in natal.items() if 1 <= nh <= 12}
        out = _read_placements(placements, gender, th, age, period="year", plain=plain)
        out["_debug"]["running_year"] = age + 1
        out["gemstones"] = _gemstones(natal_chart, out["_debug"].get("strained_planets", []), age, "year")
        return out
    except Exception as e:  # pragma: no cover
        return {"available": False, "reason": f"engine error: {e}"}


def read_month(natal_chart, birth_date, gender="", transit_houses=None, today=None, use_transit=True, plain=True):
    """LK Masik MONTH reading — annual chart advanced one house per month. Never raises."""
    try:
        age, natal, th = _prep(natal_chart, birth_date, transit_houses, today, use_transit)
        if age is None:
            return {"available": False, "reason": "missing age or natal houses"}
        try:
            from antar_engine.lal_kitab_masik import _months_since_birthday
            moff = int(_months_since_birthday(birth_date))
        except Exception:
            moff = 0
        placements = {}
        for p, nh in natal.items():
            if 1 <= nh <= 12:
                ah = get_annual_house(nh, age)
                placements[p] = ((ah - 1 + moff) % 12) + 1
        out = _read_placements(placements, gender, th, age, period="month", plain=plain)
        out["_debug"]["month_offset"] = moff
        out["gemstones"] = _gemstones(natal_chart, out["_debug"].get("strained_planets", []), age, "month")
        return out
    except Exception as e:  # pragma: no cover
        return {"available": False, "reason": f"engine error: {e}"}
