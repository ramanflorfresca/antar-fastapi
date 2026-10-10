"""[ask-direct 2026-10-10] The chart facts BEHIND an Ask answer, named and verifiable.

Competitor answers win on "Venus is your yogakaraka, sitting in the 11th with Rahu — the catch is it's
combust". Ours said "the timing shows…" and never named a fact. This builds ONE short, deterministic
line from the chart itself: the running Vimśottarī period and when its sub-period ends, the lord of the
topic's main house and where it sits (with its dignity / combustion), and the topic's significator.
No LLM, nothing inferred: every clause is read straight from chart_data / dasha_periods. English only
(other languages keep the plain answer — wrong-language text is worse than no line)."""
from datetime import date

_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_LORD = {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun",
         "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
         "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter"}
_EXALT = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo", "Jupiter": "Cancer",
          "Venus": "Pisces", "Saturn": "Libra"}
_DEBIL = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces", "Jupiter": "Capricorn",
          "Venus": "Virgo", "Saturn": "Aries"}
_COMBUST_ORB = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}
# the house that IS the topic, where CONCERN_HOUSES leads with a neighbour (love: 5th romance → 7th partner)
_PRIMARY = {"love": 7, "business": 10}
_ORD = {1: "1st", 2: "2nd", 3: "3rd"}
_TOPIC = {"career": "career", "business": "business", "wealth": "money", "finance": "money",
          "funding": "funding", "love": "relationships", "marriage": "marriage", "children": "children",
          "health": "health", "property": "property", "family": "family", "education": "studies",
          "loss": "losses", "speculation": "speculation", "legal": "legal matters"}


def _o(n):
    return _ORD.get(n, f"{n}th")


def _dignity(planet, sign, planets):
    notes = []
    if _EXALT.get(planet) == sign:
        notes.append("exalted")
    elif _DEBIL.get(planet) == sign:
        notes.append("debilitated")
    elif _LORD.get(sign) == planet:
        notes.append("in its own sign")
    sun = (planets.get("Sun") or {}).get("longitude")
    me = (planets.get(planet) or {}).get("longitude")
    orb = _COMBUST_ORB.get(planet)
    if orb and sun is not None and me is not None:
        d = abs(float(me) - float(sun)) % 360
        d = min(d, 360 - d)
        if d <= orb:
            notes.append("combust (weakened by the Sun)")
    return notes


def _period(dashas):
    rows = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
    today = date.today()

    def _d(v):
        try:
            return date.fromisoformat(str(v)[:10])
        except Exception:
            return None
    cur = {}
    for r in rows:
        lv = str(r.get("level", "")).lower()
        s, e = _d(r.get("start_date")), _d(r.get("end_date"))
        if s and e and s <= today < e:
            key = "md" if lv in ("mahadasha", "maha", "md", "1") else "ad" if lv in ("antardasha", "antar", "ad", "2") else None
            if key:
                cur[key] = (r.get("planet_or_sign") or r.get("lord_or_sign") or "", e)
    if "md" in cur and "ad" in cur:
        return f"You're running {cur['md'][0]}–{cur['ad'][0]} (sub-period ends {cur['ad'][1].strftime('%b %-d, %Y')})"
    return ""


def build_basis(concern, chart_data, dashas, language="en") -> str:
    """One line, or "" when nothing can be said truthfully."""
    try:
        if language != "en":
            return ""
        from antar_engine.ask_consultation import CONCERN_HOUSES, CONCERN_KARAKAS
        houses = CONCERN_HOUSES.get(concern)
        planets = (chart_data or {}).get("planets") or {}
        lagna = ((chart_data or {}).get("lagna") or {}).get("sign")
        if not houses or lagna not in _SIGNS or not planets:
            return ""
        bits = []
        per = _period(dashas)
        if per:
            bits.append(per + ".")
        h = _PRIMARY.get(concern, houses[0])
        sign = _SIGNS[(_SIGNS.index(lagna) + h - 1) % 12]
        lord = _LORD[sign]
        pl = planets.get(lord) or {}
        if pl.get("sign") and isinstance(pl.get("house"), int):
            notes = _dignity(lord, pl["sign"], planets)
            topic = _TOPIC.get(concern, concern)
            bits.append(f"Your {_o(h)} house ({topic}) is ruled by {lord}, which sits in your {_o(pl['house'])} house"
                        f" in {pl['sign']}" + (", " + " and ".join(notes) if notes else "") + ".")
        for k in (CONCERN_KARAKAS.get(concern) or [])[:1]:
            if k == lord:
                continue
            kp = planets.get(k) or {}
            if kp.get("sign") and isinstance(kp.get("house"), int):
                notes = _dignity(k, kp["sign"], planets)
                bits.append(f"{k}, the main significator here, is in your {_o(kp['house'])} house"
                            + (f", {' and '.join(notes)}" if notes else "") + ".")
        return " ".join(bits).strip()
    except Exception:
        return ""
