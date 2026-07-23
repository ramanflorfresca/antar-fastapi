"""
antar_engine/wealth_channel.py
How wealth reaches this person, where from, and when.          2026-07-22

Four references, each answering a different question, assembled into plain
sentences rather than another score. The scoring surface in this codebase is
already larger than its validation, so this layer explains and does not rank.

    WHAT   career_mode      owned or employed, and what kind of work
    HOW    D-10             the career chart's lagna lord — the instrument
    WHERE  Sri Lagna        the house it falls in, read as a place
    WHEN   dasha            when the channel lord is actually live

The WHERE and WHEN are the parts that were missing, and WHEN is the one that
stops this being a horoscope. A channel statement with no timing is a
compliment; with timing it is a claim.

A worked example from the chart this was built against. Sri Lagna in the 12th,
its lord Jupiter in the 2nd — wealth arrives from far away and settles into
savings. The Sri Lagna's own nakshatra is Purva Ashadha, lord Venus, so Venus is
the channel. But his next Venus antardasha is 2038, twelve years out, and
"wait for your channel lord" would be worthless advice to a man carrying debt
now.

What makes it live is the conjunction: Rahu, whose eighteen-year mahadasha
begins 13 August 2026, sits 1.78 degrees from Venus in the 11th. The channel
lord is activated by the incoming period lord rather than by its own period.
That distinction is the difference between a real timing statement and a
platitude, and it is why WHEN is computed here rather than assumed.
"""

from typing import Dict, List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
NAKSHATRA_LORDS = [
    ("Ashwini", "Ketu"), ("Bharani", "Venus"), ("Krittika", "Sun"),
    ("Rohini", "Moon"), ("Mrigashira", "Mars"), ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"), ("Pushya", "Saturn"), ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"), ("P.Phalguni", "Venus"), ("U.Phalguni", "Sun"),
    ("Hasta", "Moon"), ("Chitra", "Mars"), ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"), ("Anuradha", "Saturn"), ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"), ("P.Ashadha", "Venus"), ("U.Ashadha", "Sun"),
    ("Shravana", "Moon"), ("Dhanishta", "Mars"), ("Shatabhisha", "Rahu"),
    ("P.Bhadrapada", "Jupiter"), ("U.Bhadrapada", "Saturn"), ("Revati", "Mercury"),
]

# Where the Sri Lagna falls, said as a PLACE a person recognises. "From a
# distance" was the first phrasing and it was too vague to act on; a reader
# should be able to tell whether it describes their life.
SRI_HOUSE_PLACE = {
    1:  "close to home and under your own name",
    2:  "through what you have already built — savings, family, existing holdings",
    3:  "through your own hands and your own contacts, close by",
    4:  "through home, property, and the place you actually live",
    5:  "through what you create yourself, and through risk you choose",
    6:  "through service and daily work — the grind, not the windfall",
    7:  "through partners and clients, not alone",
    8:  "through other people's money — investors, inheritance, a sudden turn",
    9:  "through teachers, long journeys, and people senior to you",
    10: "through your public standing — being known for the work",
    11: "through networks and gains that come to you rather than are chased",
    12: "from a foreign country and a different culture, away from where you were born",
}

# What the channel lord actually is, in ordinary words.
CHANNEL_PLANET = {
    "Sun": "authority and being seen to lead",
    "Moon": "the public, and people's trust in you",
    "Mars": "drive, machinery, competition",
    "Mercury": "trade, logic, communication, product",
    "Jupiter": "counsel, teaching, reputation, expansion",
    "Venus": "what people find worth paying for — design, relationships, the deal",
    "Saturn": "endurance, structure, work nobody else will do",
    "Rahu": "the unconventional route, scale, technology",
    "Ketu": "specialised, solitary or technical work — and it cuts as often as it gives",
}


# D-2, the Hora chart, is where wealth is actually judged. Every planet falls
# into one of two signs: Leo, the Sun's hora, or Cancer, the Moon's hora. The
# product owner's instruction, and it is the classical chain — Sri Lagna, its
# nakshatra, its LORD, and then how that lord sits in D-2.
HORA_MEANING = {
    "Leo":    ("the Sun's hora", "wealth that has to be generated — earned by "
                                 "your own effort, in your own name"),
    "Cancer": ("the Moon's hora", "wealth that flows rather than is forged — it "
                                  "comes through others, and it moves"),
}
# NOT "in its own sign". In D-2 every planet falls in Cancer or Leo and nowhere
# else, so "own sign" can only ever fire for the Sun or the Moon — it is
# impossible by construction for Jupiter, Mars, Mercury, Venus and Saturn.
# Measured across 93 live charts: the rule was possible for 33% and fired for
# 18%, meaning two thirds of people could not score whatever their wealth. It
# was measuring which sign the Sri Lagna fell in, not prosperity.
#
# The real D-2 dignity is by NATURE. The Sun's hora is active and masculine,
# the Moon's receptive — so a malefic prospers in the Sun's hora and a benefic
# in the Moon's. That applies to all nine and is structurally fair.
_BENEFIC_HORA = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC_HORA = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}


def hora_wealth(chart: dict) -> Dict:
    """Where the Sri Lagna's lord sits in D-2 — the classical wealth judgement.

    Sri Lagna says where prosperity settles; its nakshatra lord says through
    what channel; this says whether the lord carrying it is placed to hold what
    it brings. Also reports how the whole chart divides between the two horas,
    which is the part that says whether wealth is forged or received.
    """
    try:
        from antar_engine.sri_lagna import sri_lagna
        sl = sri_lagna(chart)
    except Exception:
        return {"available": False}
    if not sl.get("available"):
        return {"available": False}
    lord = sl["lord"]
    d2 = ((chart.get("divisional_charts") or {}).get("d2") or {}).get("planets") or {}
    grab = lambda p: ((d2.get(p) or {}).get("sign")
                      if isinstance(d2.get(p), dict) else d2.get(p))
    seat = grab(lord)
    if seat not in HORA_MEANING:
        return {"available": False}
    hora_name, hora_desc = HORA_MEANING[seat]

    suited = ((lord in _BENEFIC_HORA and seat == "Cancer")
              or (lord in _MALEFIC_HORA and seat == "Leo"))

    sun_h = [p for p in d2 if grab(p) == "Leo"]
    moon_h = [p for p in d2 if grab(p) == "Cancer"]

    line = (f"In the wealth chart your prosperity lord {lord} sits in {hora_name} "
            f"— {hora_desc}.")
    if suited:
        line += (f" {lord} is suited to that hora, so what it brings, it is "
                 f"placed to hold.")
    else:
        line += (f" {lord} is not naturally at home there — money arrives but "
                 f"has to be worked to stay.")
    if len(sun_h) >= 6:
        line += (" And most of your chart sits in the Sun's hora: wealth here is "
                 "forged rather than received.")
    elif len(moon_h) >= 6:
        line += (" And most of your chart sits in the Moon's hora: wealth here "
                 "arrives through others more than through force.")

    return {"available": True, "lord": lord, "hora": seat,
            "hora_name": hora_name, "suited": suited,
            "sun_hora_count": len(sun_h), "moon_hora_count": len(moon_h),
            "line": line}


def _nakshatra_of(longitude: float) -> tuple:
    idx = int((longitude % 360) // (360.0 / 27)) % 27
    return NAKSHATRA_LORDS[idx]


def wealth_channel(chart: dict, dashas: Optional[dict] = None) -> Dict:
    """Where wealth comes from, through what, and when that becomes live."""
    try:
        from antar_engine.sri_lagna import sri_lagna
        sl = sri_lagna(chart)
    except Exception:
        return {"available": False}
    if not sl.get("available"):
        return {"available": False}

    nak_name, channel = _nakshatra_of(sl["longitude"])
    house = sl["house_from_lagna"]
    sl_lord = sl["lord"]
    lord_house = ((chart.get("planets") or {}).get(sl_lord) or {}).get("house")

    lines: List[str] = []
    lines.append(f"Wealth reaches you {SRI_HOUSE_PLACE.get(house, 'through this area of life')}.")
    if lord_house:
        lines.append(f"Its lord {sl_lord} sits in your {_ord(lord_house)} house, "
                     f"which is where it ends up once it arrives.")
    lines.append(f"The channel is {channel} — {CHANNEL_PLANET.get(channel, '')}.")
    hw = hora_wealth(chart)
    if hw.get("available"):
        lines.append(hw["line"])

    # WHEN. Two ways the channel goes live: its own period, or a period lord
    # sitting on it. The second is the one people miss, and on the chart this
    # was built against it is the only one that happens this decade.
    timing = _channel_timing(chart, channel, dashas)
    lines.extend(timing["lines"])

    return {
        "available": True,
        "sri_lagna_sign": sl["sign"],
        "sri_lagna_house": house,
        "sri_lagna_lord": sl_lord,
        "sri_lagna_lord_house": lord_house,
        "channel_nakshatra": nak_name,
        "channel_planet": channel,
        "timing": timing,
        "lines": lines,
    }


def _lagna_index(chart):
    return (chart.get('lagna') or {}).get('sign_index', 0)


def wealth_windows(chart: dict, dashas: Optional[dict], birth) -> Dict:
    """When the wealth periods actually run — ANTARDASHA level, plus chara dasha.

    The first version of this counted mahadashas only, and told a founder
    currently running a SaaS at about $1M ARR that he had ZERO wealth years
    remaining. His success was happening inside an antardasha the model could
    not see. A sixteen-year mahadasha is not the resolution at which businesses
    succeed — and every timing finding that has survived scrutiny in this
    codebase landed on an ANTARDASHA lord, never a mahadasha.

    It also told a 35-year-old carrying heavy debt that his first opportunity
    was at 55. That is the kind of claim no chart supports at that resolution,
    and the harm of being wrong is one-sided.

    A wealth-giver is the lord of the 2nd, 11th or 9th, or any planet sitting in
    the 2nd or 11th.
    """
    from datetime import date as _date
    out = {"running": [], "next": [], "chara": None, "years_ahead": 0.0}
    if not dashas or not birth:
        return out
    li = (chart.get("lagna") or {}).get("sign_index", 0) or 0
    lord = lambda h: SIGN_LORD[(li + h - 1) % 12]
    givers = {lord(h) for h in (2, 11, 9)}
    for p, d in (chart.get("planets") or {}).items():
        if isinstance(d, dict) and d.get("house") in (2, 11):
            givers.add(p)

    today = _date.today()
    age = (today - birth).days / 365.25
    for r in (dashas.get("vimsottari") or []):
        if not isinstance(r, dict):
            continue
        lvl = str(r.get("level") or "").lower()
        if lvl not in ("mahadasha", "antardasha"):
            continue
        who = r.get("lord_or_sign") or r.get("planet_or_sign")
        if who not in givers:
            continue
        try:
            s = _date.fromisoformat(str(r.get("start_date"))[:10])
            e = _date.fromisoformat(str(r.get("end_date"))[:10])
        except Exception:
            continue
        a0 = (s - birth).days / 365.25
        if lvl == "antardasha":
            lo, hi = max(a0, age, 25), min((e - birth).days / 365.25, 70)
            if hi > lo:
                out["years_ahead"] += hi - lo
        if s <= today <= e:
            out["running"].append({"level": lvl, "lord": who, "ends": e.isoformat()})
        elif s > today and a0 < 70:
            out["next"].append({"level": lvl, "lord": who, "starts": s.isoformat(),
                                "ends": e.isoformat(), "age": round(a0)})
    out["next"].sort(key=lambda x: x["starts"])
    out["next"] = out["next"][:4]
    # Chara dasha as the second opinion, per the owner's instruction that a
    # wealth reading should carry it alongside Vimshottari.
    for r in (dashas.get("jaimini") or []):
        if not isinstance(r, dict):
            continue
        s, e = str(r.get("start_date"))[:10], str(r.get("end_date"))[:10]
        if s and e and s <= today.isoformat() <= e:
            out["chara"] = {"sign": r.get("planet_or_sign") or r.get("lord_or_sign"),
                            "until": e}
            break
    out["years_ahead"] = round(out["years_ahead"], 1)
    return out


def _ord(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _channel_timing(chart: dict, channel: str, dashas: Optional[dict]) -> Dict:
    """When the channel lord is actually active — by its own period, or by contact."""
    from datetime import date
    out = {"lines": [], "own_period": None, "activated_by": None}
    today = date.today().isoformat()

    # 1. A conjunction with an incoming or running period lord activates the
    #    channel without waiting for the channel's own dasha. Same house, close
    #    degrees — this is what makes a distant period lord relevant now.
    planets = (chart or {}).get("planets") or {}
    ch = planets.get(channel) or {}
    ch_lon, ch_house = ch.get("longitude"), ch.get("house")
    conjuncts = []
    if isinstance(ch_lon, (int, float)):
        for p, d in planets.items():
            if p == channel or not isinstance(d, dict):
                continue
            lon = d.get("longitude")
            if isinstance(lon, (int, float)) and d.get("house") == ch_house:
                sep = abs(((lon - ch_lon + 180) % 360) - 180)
                if sep <= 8.0:
                    conjuncts.append((p, round(sep, 2)))

    # 2. The channel lord's own upcoming periods.
    nxt = None
    if dashas:
        for r in (dashas.get("vimsottari") or []):
            if not isinstance(r, dict):
                continue
            lord = r.get("lord_or_sign") or r.get("planet_or_sign")
            lvl = str(r.get("level") or "").lower()
            end = str(r.get("end_date") or "")[:10]
            start = str(r.get("start_date") or "")[:10]
            if lord == channel and lvl in ("mahadasha", "antardasha") and end >= today:
                if nxt is None or start < nxt[0]:
                    nxt = (start, end, lvl)
    out["own_period"] = nxt

    if conjuncts:
        ordered = [p for p, _ in sorted(conjuncts, key=lambda x: x[1])]
        names = ordered[0] if len(ordered) == 1 else (
            " and ".join([", ".join(ordered[:-1]), ordered[-1]]))
        verb = "sits" if len(ordered) == 1 else "sit"
        out["activated_by"] = ordered
        out["lines"].append(
            f"{names} {verb} with {channel} in the same house, within a few degrees. "
            f"So any period belonging to {names} switches the channel on — it does "
            f"not have to wait for {channel}'s own period.")

    if nxt:
        far = nxt[0][:4]
        if conjuncts and int(far) - int(today[:4]) > 5:
            out["lines"].append(
                f"{channel}'s own period is not until {far}, which is why the "
                f"conjunction above matters more than waiting for it.")
        else:
            out["lines"].append(
                f"{channel}'s own {nxt[2]} runs {nxt[0]} to {nxt[1]} — the stretch "
                f"where this channel carries the most weight on its own.")
    elif not conjuncts:
        out["lines"].append(
            f"No {channel} period is on record ahead, and nothing sits with it — "
            f"this channel works quietly rather than in bursts.")

    return out
