"""
lk_varshphal_year.py — deterministic Lal Kitab Varshphal (year) reading engine.

PREVIEW / flagged — NOT wired as the live This Year yet. It reads the rule data
from `lk_year_rules` + the authentic annual progression table, and degrades
gracefully where book cells aren't extracted yet (falls back to significator +
house meaning). As the rule tables fill in, the output sharpens automatically.

Doctrine (founder + Roop Chand books):
  annual house  = VARSHAPHAL_TABLE[running_year][natal_house]   (the "age" half)
  + current transit overlay (slow planets into the annual / 8th houses)
  read each lit planet:  significator × annual-house × dusthana/8th-event × bait
  -> what will happen · what to avoid · the LK remedy · life-event flag
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

_PRIORITY = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
_SLOW = ("Saturn", "Jupiter", "Rahu", "Ketu")


def _age(birth_date, today=None):
    try:
        b = date.fromisoformat(str(birth_date)[:10])
    except Exception:
        return None
    t = today or date.today()
    a = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    return max(0, a)


def _house_domain(h):
    return (HOUSE_KARAKAS.get(h, "") or "").split(",")[0].strip() or f"house {h}"


def _remedy_text(planet, house):
    pr = _LK_REMEDIES.get(planet) or {}
    obj = pr.get(house) or pr.get("general")
    if obj is None:
        return None
    return getattr(obj, "instructions", None) or (obj.get("instructions") if isinstance(obj, dict) else None)


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


def read_year(natal_chart, birth_date, gender="", transit_houses=None, today=None):
    """Return the LK Varshphal year reading. Never raises."""
    try:
        age = _age(birth_date, today)
        natal = _natal_houses(natal_chart)
        if age is None or not natal:
            return {"available": False, "reason": "missing age or natal houses"}

        spouse = R.spouse_karaka(gender)
        placements = {}          # planet -> annual house this year
        for p, nh in natal.items():
            if 1 <= nh <= 12:
                placements[p] = get_annual_house(nh, age)

        happen, avoid, remedies, events = [], [], [], []
        n_support = n_strain = 0

        for p in _PRIORITY:
            ah = placements.get(p)
            if not ah:
                continue
            sig = R.planet_significations(p, gender)
            domain = sig[0] if sig else _house_domain(ah)
            verdict = (R.LK_HOUSE_VERDICTS.get(p, {}) or {}).get(ah)

            strained = ah in R.DUSTHANA
            supported = ah in (R.KENDRA + R.TRIKONA) or (p == "Saturn" and ah in R.SATURN_BENEFIC_HOUSES)

            # transit amplifier: a slow planet currently in this annual house (or 8th)
            t_hit = False
            if isinstance(transit_houses, dict):
                for sp in _SLOW:
                    if transit_houses.get(sp) in (ah, R.EVENT_HOUSE):
                        t_hit = True
                        break

            if strained:
                n_strain += 1
                what = verdict.get("bad") if (verdict and verdict.get("bad")) else f"pressure on {domain}"
                line = f"{domain.capitalize()}: {what}."
                bait = R.LK_BAIT_TRANSFER.get(p)
                if bait and bait.get("suffers"):
                    line += f" The strain can surface through {bait['suffers']}."
                happen.append(line)
                avoid.append(f"Don't force big moves in {domain} this year.")
                # prefer the book's "Sr. No." remedy (resolved from the verdict
                # refs) over the partial REMEDIES table
                rt = None
                if verdict and verdict.get("refs") and R.LK_REMEDY_LIST.get(p):
                    for _ref in verdict["refs"]:
                        _t = R.LK_REMEDY_LIST[p].get(_ref)
                        if _t:
                            rt = _t
                            break
                if not rt:
                    rt = _remedy_text(p, ah)
                if rt:
                    remedies.append({"planet": p, "house": ah, "text": rt})
                if ah == R.EVENT_HOUSE or t_hit:
                    if p == spouse:
                        tag = "your husband and marriage" if spouse == "Jupiter" else "your wife and marriage"
                    else:
                        tag = domain
                    events.append(f"A sudden, unexpected turn around {tag} (loss or unexpected gain) is possible this year.")
            elif supported:
                n_support += 1
                what = verdict.get("good") if (verdict and verdict.get("good")) else f"strength in {domain}"
                happen.append(f"{domain.capitalize()}: {what}.")

        if n_support and not n_strain:
            v = "supportive"
        elif n_strain and not n_support:
            v = "challenging"
        else:
            v = "mixed"

        return {
            "available": True,
            "verdict": v,
            "what_will_happen": happen[:6],
            "what_to_avoid": avoid[:4],
            "remedies": remedies[:4],
            "life_events": events[:3],
            "_debug": {
                "age": age, "running_year": age + 1, "gender": gender,
                "spouse_karaka": spouse, "annual_placements": placements,
                "transit_used": bool(transit_houses),
                "rule_coverage": {p: sorted((R.LK_HOUSE_VERDICTS.get(p) or {}).keys()) for p in _PRIORITY if R.LK_HOUSE_VERDICTS.get(p)},
            },
        }
    except Exception as e:  # pragma: no cover
        return {"available": False, "reason": f"engine error: {e}"}
