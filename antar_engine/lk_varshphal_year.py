"""
lk_varshphal_year.py — deterministic Lal Kitab Varshphal (year) reading engine.

PREVIEW / flagged — NOT the live This Year yet. Reads the rule data from
`lk_year_rules` + the authentic annual progression table, and degrades
gracefully where data is missing.

Layers:
  1. SINGLE planet:  annual house (VARSHAPHAL_TABLE) -> significator × house
     verdict × dusthana/8th-event × bait/transfer + the LK remedy.
  2. COMBINATION:    when 2+ planets share an annual house — friend/foe
     (friend strengthens, foe spoils) + the book's two-planet "acts-as"
     combinations (Rahu+Ketu→artificial Venus, Saturn+Jupiter→virtuous, …).
  3. TRANSIT:        current slow planets (Saturn/Jupiter/Rahu/Ketu) into the
     annual house or the 8th — amplifies events (malefic) or eases (Jupiter).
"""
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


def _age(birth_date, today=None):
    try:
        b = date.fromisoformat(str(birth_date)[:10])
    except Exception:
        return None
    t = today or date.today()
    return max(0, t.year - b.year - ((t.month, t.day) < (b.month, b.day)))


def _house_domain(h):
    return (HOUSE_KARAKAS.get(h, "") or "").split(",")[0].strip() or f"house {h}"


def _remedy_text(planet, house):
    pr = _LK_REMEDIES.get(planet) or {}
    obj = pr.get(house) or pr.get("general")
    if obj is None:
        return None
    return getattr(obj, "instructions", None) or (obj.get("instructions") if isinstance(obj, dict) else None)


def _book_remedy(planet, verdict):
    if verdict and verdict.get("refs") and R.LK_REMEDY_LIST.get(planet):
        for ref in verdict["refs"]:
            t = R.LK_REMEDY_LIST[planet].get(ref)
            if t:
                return t
    return _remedy_text(planet, verdict.get("_house") if verdict else None)


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
    sign = None
    if isinstance(lg, dict):
        sign = lg.get("sign") or lg.get("rashi")
    elif isinstance(lg, str):
        sign = lg
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


def read_year(natal_chart, birth_date, gender="", transit_houses=None, today=None, use_transit=True):
    """Return the LK Varshphal year reading (single + combination + transit). Never raises."""
    try:
        age = _age(birth_date, today)
        natal = _natal_houses(natal_chart)
        if age is None or not natal:
            return {"available": False, "reason": "missing age or natal houses"}

        spouse = R.spouse_karaka(gender)
        placements = {p: get_annual_house(nh, age) for p, nh in natal.items() if 1 <= nh <= 12}

        # transit overlay (auto-compute if not supplied)
        if transit_houses is None and use_transit:
            transit_houses = transit_houses_now(_lagna_index(natal_chart), today=today)
        transit_houses = transit_houses or {}

        # group annual placements by house for the combination layer
        occupants = {}
        for p, ah in placements.items():
            occupants.setdefault(ah, []).append(p)

        # ── COMBINATION layer: book two-planet "acts-as" rules ──
        combinations = []
        for ah, plist in occupants.items():
            if len(plist) < 2:
                continue
            for a, b, eff in R.LK_COMBINATIONS:
                if a in plist and b in plist:
                    if "4th house" in eff and ah != 4:
                        continue
                    combinations.append(f"In your {_house_domain(ah)}, {a} and {b} together — {eff}.")

        happen, avoid, remedies, events, notes = [], [], [], [], []
        n_support = n_strain = 0

        for p in _PRIORITY:
            ah = placements.get(p)
            if not ah:
                continue
            sig = R.planet_significations(p, gender)
            domain = sig[0] if sig else _house_domain(ah)
            verdict = dict((R.LK_HOUSE_VERDICTS.get(p, {}) or {}).get(ah) or {})
            verdict["_house"] = ah

            # friend/foe among co-occupants of the same annual house
            co = [x for x in occupants.get(ah, []) if x != p]
            ff = R.LK_FRIEND_FOE.get(p, {})
            foes_here = [x for x in co if x in ff.get("foes", [])]
            friends_here = [x for x in co if x in ff.get("friends", [])]

            base_strained = ah in R.DUSTHANA
            base_supported = ah in (R.KENDRA + R.TRIKONA) or (p == "Saturn" and ah in R.SATURN_BENEFIC_HOUSES)

            # combination adjustment
            spoiled = bool(foes_here) and not friends_here
            eased = bool(friends_here) and not foes_here

            strained = base_strained or (spoiled and not base_supported)
            supported = (base_supported or eased) and not strained

            # transit overlay for this house
            t_here = [sp for sp in _SLOW if transit_houses.get(sp) == ah]
            t_malefic = [sp for sp in t_here if sp in _MALEFIC_TRANSIT]
            t_event = [sp for sp in _MALEFIC_TRANSIT if transit_houses.get(sp) == R.EVENT_HOUSE]

            if strained:
                n_strain += 1
                what = verdict.get("bad") or f"pressure on {domain}"
                line = f"{domain.capitalize()}: {what}."
                bait = R.LK_BAIT_TRANSFER.get(p)
                if bait and bait.get("suffers"):
                    line += f" The strain can surface through {bait['suffers']}."
                if foes_here:
                    line += f" ({', '.join(foes_here)} shares this area and spoils it.)"
                if t_malefic:
                    line += f" Transiting {', '.join(t_malefic)} sharpens it this year."
                happen.append(line)
                avoid.append(f"Don't force big moves in {domain} this year.")
                rt = _book_remedy(p, verdict)
                if rt:
                    remedies.append({"planet": p, "house": ah, "text": rt})
                if ah == R.EVENT_HOUSE or t_malefic or (p in t_event):
                    if p == spouse:
                        tag = "your husband and marriage" if spouse == "Jupiter" else "your wife and marriage"
                    else:
                        tag = domain
                    events.append(f"A sudden, unexpected turn around {tag} (loss or unexpected gain) is possible this year.")
            elif supported:
                n_support += 1
                what = verdict.get("good") or f"strength in {domain}"
                line = f"{domain.capitalize()}: {what}."
                if friends_here:
                    line += f" ({', '.join(friends_here)} shares this area and strengthens it.)"
                if "Jupiter" in t_here:
                    line += " Transiting Jupiter eases this area this year."
                happen.append(line)

            # note where a kendra/trikona placement is spoiled by a foe
            if base_supported and foes_here:
                notes.append(f"{domain.capitalize()} is well placed but {', '.join(foes_here)} can spoil it — handle with care.")

        verdict_overall = "supportive" if (n_support and not n_strain) else ("challenging" if (n_strain and not n_support) else "mixed")

        return {
            "available": True,
            "verdict": verdict_overall,
            "what_will_happen": happen[:7],
            "what_to_avoid": avoid[:5],
            "remedies": remedies[:5],
            "life_events": events[:4],
            "combinations": combinations[:4],
            "notes": notes[:3],
            "_debug": {
                "age": age, "running_year": age + 1, "gender": gender,
                "spouse_karaka": spouse, "annual_placements": placements,
                "shared_houses": {h: ps for h, ps in occupants.items() if len(ps) >= 2},
                "transit_houses": transit_houses,
            },
        }
    except Exception as e:  # pragma: no cover
        return {"available": False, "reason": f"engine error: {e}"}
